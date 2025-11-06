from __future__ import annotations
import time
import random
from typing import Optional, Dict, Tuple, List, Any, cast
import chess
import chess.engine
import chess.syzygy
from lib.engine_wrapper import MinimalEngine
from engines.time_manager import TimeManager
from engines.opening import OpeningsMixin, Opening
from engines.eval import EvaluationMixin

INF = 10_000_000
MATE_SCORE = 1_000_000


class DragonBot(MinimalEngine, OpeningsMixin, EvaluationMixin):
    def __init__(self, commands, options, stderr, draw_or_resign, game=None, **popen_args) -> None:
        super().__init__(commands, options, stderr, draw_or_resign, game, name="DragonBot")

        self.max_depth: int = 20
        self.max_nodes: Optional[int] = None
        self.tb_paths: List[str] = []
        self.tb_probe_limit: int = 7
        self.book_paths: List[str] = []
        self.use_book: bool = False
        self.randomize_book: bool = True
        self.book_min_weight: int = 1

        self.use_csv_openings: bool = True
        self.csv_opening_path: str = "engines/oppenings.csv"
        self.csv_openings: List[Opening] = []
        self._load_csv_openings()

        self.tt_size: int = 16_777_216
        self.tt: Dict[int, "TTEntry"] = {}
        self.age: int = 0
        self.pv_table: Dict[int, chess.Move] = {}
        self.killer_moves: Dict[int, List[chess.Move]] = {}
        self.history_heuristic: Dict[Tuple[bool, int, int], int] = {}
        self.counter_moves: Dict[Tuple[Optional[int], Optional[int]], chess.Move] = {}
        self.nodes: int = 0
        self.start_time: float = 0.0
        self.time_budget: float = 0.0
        self.stop: bool = False
        self.tb: Optional[chess.syzygy.Tablebase] = None

        self.pst_mg, self.pst_eg = self._init_pst()

        self.PASSED_PAWN_BONUS = [0, 10, 20, 40, 60, 90, 130, 0]
        self.DOUBLED_PAWN_PENALTY = 15
        self.ISOLATED_PAWN_PENALTY = 20
        self.BACKWARD_PAWN_PENALTY = 12
        self.ROOK_OPEN_FILE_BONUS = 25
        self.ROOK_SEMI_OPEN_FILE_BONUS = 15
        self.BISHOP_PAIR_BONUS = 30
        self.KNIGHT_OUTPOST_BONUS = 25
        self.KING_SHIELD_BONUS = 8
        self.KING_ATTACK_WEIGHT = 10
        self.MATE_SCORE = MATE_SCORE

        self.time_manager = TimeManager()

    def notify(self, method_name: str, *args, **kwargs) -> Any:
        if method_name == "configure":
            self._configure(options=args[0] if args else kwargs)
            return None
        if method_name in ("ping", "close", "quit"):
            return None
        if method_name == "send_opponent_information":
            return None
        if method_name == "send_game_result":
            self.tt.clear()
            self.history_heuristic.clear()
            self.killer_moves.clear()
            self.counter_moves.clear()
            return None
        return None

    def _configure(self, options: Dict[str, Any]) -> None:
        depth = options.get("Depth")
        if isinstance(depth, int) and depth > 0:
            self.max_depth = depth

        nodes = options.get("Nodes")
        if isinstance(nodes, int) and nodes > 0:
            self.max_nodes = nodes

        tb_path = options.get("SyzygyPath")
        if tb_path:
            self.tb_paths = tb_path if isinstance(tb_path, list) else [tb_path]
            self._open_tb()

        tblimit = options.get("TablebaseProbeLimit")
        if isinstance(tblimit, int) and 3 <= tblimit <= 7:
            self.tb_probe_limit = tblimit

        use_book = options.get("UseBook")
        if isinstance(use_book, bool):
            self.use_book = use_book

        book_paths = options.get("Book")
        if book_paths:
            self.book_paths = book_paths if isinstance(book_paths, list) else [book_paths]

        book_min_weight = options.get("BookMinWeight")
        if isinstance(book_min_weight, int) and 0 <= book_min_weight <= 65535:
            self.book_min_weight = book_min_weight

        use_csv = options.get("UseCSVOpenings")
        if isinstance(use_csv, bool):
            self.use_csv_openings = use_csv

        csv_path = options.get("CSVOpeningsPath")
        if isinstance(csv_path, str) and csv_path:
            if csv_path != self.csv_opening_path or not self.csv_openings:
                self.csv_opening_path = csv_path
                self._load_csv_openings()

    def search(self, board: chess.Board, time_limit: chess.engine.Limit, ponder: bool,
               draw_offered: bool, root_moves):
        csv_pick = self._find_csv_opening_move(board)
        if csv_pick:
            move, opening_name = csv_pick
            info = cast(chess.engine.InfoDict, {
                "string": f"lichess-bot-source:CSV Opening - {opening_name}",
                "depth": 0,
                "nodes": 0,
                "pv": [move]
            })
            return chess.engine.PlayResult(move, None, info)

        if self.use_book and self.book_paths and len(board.move_stack) < 2 * self.max_depth:
            move = self._book_move(board)
            if move is not None:
                info = cast(chess.engine.InfoDict, {
                    "string": "lichess-bot-source:Polyglot Opening Book",
                    "depth": 0,
                    "nodes": 0,
                    "pv": [move]
                })
                return chess.engine.PlayResult(move, None, info)

        if self.tb is not None and self._tb_in_range(board):
            tb_move = self._tb_best_move(board)
            if tb_move is not None:
                info = cast(chess.engine.InfoDict, {
                    "string": "lichess-bot-source:Syzygy EGTB",
                    "depth": 0,
                    "nodes": 0,
                    "pv": [tb_move]
                })
                return chess.engine.PlayResult(tb_move, None, info)

        self.start_time = time.perf_counter()
        self.nodes = 0
        self.stop = False

        allocated_time, adaptive_max_depth = self.time_manager.calculate_time_allocation(board, time_limit, self.max_depth)

        print(f"Allocated time: {allocated_time:.3f}s, Target depth: {adaptive_max_depth}")

        self.time_budget = allocated_time
        safety_margin = min(0.1, 0.05 * max(1.0, self.time_budget))
        self.time_deadline = self.start_time + max(0.05, self.time_budget - safety_margin)
        self.age += 1

        if self.age % 4 == 0:
            self.killer_moves = {k: v for k, v in self.killer_moves.items() if k < 50}

        best_move: Optional[chess.Move] = None
        best_score = 0
        pv: List[chess.Move] = []
        last_depth = 0
        allowed_root: Optional[set[chess.Move]] = None
        if isinstance(root_moves, list):
            allowed_root = set(root_moves)

        self.pv_table.clear()
        score, move = self._pvs(board, 1, -INF, INF, 0, True, allowed_root)
        if move is not None:
            best_move = move
            best_score = score
            pv = self._extract_pv(board)
        last_depth = 1

        stopped_reason = "reached max depth"
        for depth in range(2, adaptive_max_depth + 1):
            if self._time_up():
                stopped_reason = "time up"
                break

            self.pv_table.clear()

            alpha = max(-INF, best_score - 50)
            beta = min(INF, best_score + 50)

            score, move = self._pvs(board, depth, alpha, beta, 0, True, allowed_root)

            if score <= alpha or score >= beta:
                score, move = self._pvs(board, depth, -INF, INF, 0, True, allowed_root)

            last_depth = depth
            if move is not None:
                best_move = move
                best_score = score
                pv = self._extract_pv(board)

            if self._time_up():
                stopped_reason = "time up"
                break

            if self.max_nodes and self.nodes >= self.max_nodes:
                stopped_reason = "nodes limit"
                break

            if abs(best_score) > MATE_SCORE - 100:
                stopped_reason = "mate found"
                break

        time_used = time.perf_counter() - self.start_time
        print(f"Stopped at depth {last_depth} due to {stopped_reason}, time used: {time_used:.3f}s")

        legal_moves_list = list(board.legal_moves)
        if best_move is None:
            moves = legal_moves_list if allowed_root is None else [m for m in legal_moves_list if m in allowed_root]
            best_move = random.choice(moves) if moves else None

        info = cast(
            chess.engine.InfoDict,
            {
                "string": "lichess-bot-source:Engine",
                "depth": last_depth,
                "nodes": self.nodes,
                "nps": int(self.nodes / max(1e-3, time.perf_counter() - self.start_time)),
                "pv": pv,
                "score": chess.engine.PovScore(chess.engine.Cp(best_score), board.turn),
            },
        )
        return chess.engine.PlayResult(best_move, None, info)

    def _pvs(self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int,
             is_pv: bool, allowed_root: Optional[set[chess.Move]] = None) -> Tuple[int, Optional[chess.Move]]:
        if self._time_up():
            return 0, None

        self.nodes += 1

        if board.is_checkmate():
            return -MATE_SCORE + ply, None
        if board.is_stalemate() or board.is_insufficient_material():
            return 0, None
        if board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
            return 0, None

        alpha = max(alpha, -MATE_SCORE + ply)
        beta = min(beta, MATE_SCORE - ply - 1)
        if alpha >= beta:
            return alpha, None

        key = self._hash_key(board)
        entry = self.tt.get(key)
        tt_move = entry.best_move if entry else None

        if entry and entry.depth >= depth and not is_pv:
            tscore = entry.score
            if entry.flag == 0:
                return tscore, entry.best_move
            if entry.flag < 0 and tscore <= alpha:
                return alpha, entry.best_move
            if entry.flag > 0 and tscore >= beta:
                return beta, entry.best_move

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply), None

        is_check = board.is_check()

        if (not is_pv and not is_check and depth >= 3 and
                self._has_non_pawn_material(board, board.turn)):
            R = 3 if depth > 6 else 2
            board.push(chess.Move.null())
            null_score, _ = self._pvs(board, depth - 1 - R, -beta, -beta + 1, ply + 1, False)
            null_score = -null_score
            board.pop()
            if null_score >= beta:
                return beta, None

        if is_pv and tt_move is None and depth >= 4:
            _, iid_move = self._pvs(board, depth - 2, alpha, beta, ply, True)
            if iid_move:
                tt_move = iid_move

        if depth <= 3 and not is_pv and not is_check and abs(alpha) < MATE_SCORE - 100:
            futility_margin = [0, 200, 350, 500][depth]
            static_eval = self._evaluate(board)
            if static_eval + futility_margin <= alpha:
                return alpha, None

        best_move: Optional[chess.Move] = None
        best_score = -INF
        orig_alpha = alpha
        moves_searched = 0

        moves = self._ordered_moves(board, tt_move, ply)
        if allowed_root is not None and ply == 0:
            moves = [m for m in moves if m in allowed_root]

        if not moves:
            return 0, None

        if is_check:
            depth += 1

        for i, move in enumerate(moves):
            board.push(move)

            do_reduction = False
            reduction = 0
            if (not is_pv and moves_searched >= 4 and depth >= 3 and
                    not is_check and not board.is_check() and
                    not board.is_capture(move) and move.promotion is None):
                reduction = 1
                if moves_searched >= 8:
                    reduction = 2
                if depth > 6:
                    reduction += 1
                do_reduction = True

            if moves_searched == 0:
                score, _ = self._pvs(board, depth - 1, -beta, -alpha, ply + 1, is_pv)
                score = -score
            else:
                if do_reduction:
                    score, _ = self._pvs(board, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, False)
                    score = -score
                else:
                    score = alpha + 1

                if score > alpha and do_reduction:
                    score, _ = self._pvs(board, depth - 1, -alpha - 1, -alpha, ply + 1, False)
                    score = -score

                if score > alpha and score < beta:
                    score, _ = self._pvs(board, depth - 1, -beta, -alpha, ply + 1, is_pv)
                    score = -score

            board.pop()
            moves_searched += 1

            if score > best_score:
                best_score = score
                best_move = move
                if score > alpha:
                    alpha = score
                    self.pv_table[key] = move
                    if alpha >= beta:
                        self._update_history(board, move, depth)
                        if not board.is_capture(move):
                            self._update_killers(ply, move)
                            if len(board.move_stack) > 0:
                                prev_move = board.peek()
                                self.counter_moves[(prev_move.from_square, prev_move.to_square)] = move
                        break

            if self._time_up():
                break

        flag = 0
        if best_score <= orig_alpha:
            flag = -1
        elif best_score >= beta:
            flag = 1

        self._store_tt(key, TTEntry(depth=depth, score=best_score, flag=flag,
                                    best_move=best_move, age=self.age))

        return best_score, best_move

    def _quiescence(self, board: chess.Board, alpha: int, beta: int, ply: int) -> int:
        if self._time_up():
            return 0

        self.nodes += 1

        key = self._hash_key(board)
        entry = self.tt.get(key)
        if entry and entry.depth >= 0:
            tscore = entry.score
            if entry.flag == 0:
                return tscore
            if entry.flag < 0 and tscore <= alpha:
                return alpha
            if entry.flag > 0 and tscore >= beta:
                return beta

        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta

        BIG_DELTA = 975
        if stand_pat < alpha - BIG_DELTA:
            return alpha

        if alpha < stand_pat:
            alpha = stand_pat

        orig_alpha = alpha

        for move in self._ordered_captures(board):
            if not board.gives_check(move) and self._see(board, move) < 0:
                continue

            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, ply + 1)
            board.pop()

            if score >= beta:
                self._store_tt(key, TTEntry(depth=0, score=beta, flag=1, best_move=move, age=self.age))
                return beta

            if score > alpha:
                alpha = score

            if self._time_up():
                break

        flag = 0 if alpha > orig_alpha else -1
        self._store_tt(key, TTEntry(depth=0, score=alpha, flag=flag, best_move=None, age=self.age))

        return alpha

    def _store_tt(self, key: int, entry: "TTEntry") -> None:
        existing = self.tt.get(key)
        if existing:
            if entry.depth >= existing.depth or entry.age >= existing.age:
                self.tt[key] = entry
        else:
            if len(self.tt) >= self.tt_size:
                if random.random() < 0.05:
                    old_age = self.age - 8
                    self.tt = {k: v for k, v in self.tt.items() if v.age > old_age}
            self.tt[key] = entry

    def _see(self, board: chess.Board, move: chess.Move) -> int:
        if not board.is_capture(move):
            return 0

        from_sq = move.from_square
        to_sq = move.to_square
        captured = board.piece_at(to_sq)
        attacker = board.piece_at(from_sq)

        if captured is None or attacker is None:
            return 0

        gain = self._piece_value(captured.piece_type)

        board.push(move)
        is_attacked = board.is_attacked_by(not board.turn, to_sq)
        board.pop()

        if is_attacked:
            gain -= self._piece_value(attacker.piece_type)

        return gain

    def _ordered_moves(self, board: chess.Board, tt_move: Optional[chess.Move],
                       ply: int) -> List[chess.Move]:
        moves = list(board.legal_moves)

        killers = self.killer_moves.get(ply, [])
        killer_set = set(killers)

        prev_move = board.peek() if len(board.move_stack) > 0 else None
        counter_move = None
        if prev_move:
            counter_move = self.counter_moves.get((prev_move.from_square, prev_move.to_square))

        def score(m: chess.Move) -> int:
            if tt_move and m == tt_move:
                return 10000000

            s = 0

            if board.is_capture(m):
                victim = board.piece_at(m.to_square)
                attacker = board.piece_at(m.from_square)
                if victim and attacker:
                    mvv_lva = self._piece_value(victim.piece_type) * 100 - self._piece_value(attacker.piece_type)
                    s += mvv_lva + 100000

                    see_score = self._see(board, m)
                    if see_score > 0:
                        s += see_score

            if m.promotion == chess.QUEEN:
                s += 900000
            elif m.promotion:
                s += 300000

            if board.gives_check(m):
                s += 50000

            piece = board.piece_at(m.from_square)
            if piece:
                to_sq = m.to_square
                from_sq = m.from_square

                if piece.piece_type == chess.PAWN:
                    rank = chess.square_rank(to_sq)
                    if piece.color == chess.WHITE and rank >= 5:
                        s += (rank - 4) * 10000
                    elif piece.color == chess.BLACK and rank <= 2:
                        s += (3 - rank) * 10000

                center_distance_from = abs(chess.square_file(from_sq) - 3.5) + abs(chess.square_rank(from_sq) - 3.5)
                center_distance_to = abs(chess.square_file(to_sq) - 3.5) + abs(chess.square_rank(to_sq) - 3.5)
                if center_distance_to < center_distance_from:
                    s += int((center_distance_from - center_distance_to) * 1000)

            if m in killer_set:
                s += 80000
            elif counter_move and m == counter_move:
                s += 70000

            s += self.history_heuristic.get((board.turn, m.from_square, m.to_square), 0)

            return s

        moves.sort(key=score, reverse=True)
        return moves

    def _ordered_captures(self, board: chess.Board) -> List[chess.Move]:
        caps = [m for m in board.legal_moves
                if board.is_capture(m) or m.promotion == chess.QUEEN]

        def mvv_lva(m: chess.Move) -> int:
            score = 0
            if board.is_capture(m):
                victim = board.piece_at(m.to_square)
                attacker = board.piece_at(m.from_square)
                if victim and attacker:
                    score = self._piece_value(victim.piece_type) * 10 - self._piece_value(attacker.piece_type)
            if m.promotion == chess.QUEEN:
                score += 9000
            return score

        caps.sort(key=mvv_lva, reverse=True)
        return caps

    def _update_history(self, board: chess.Board, move: chess.Move, depth: int) -> None:
        key = (board.turn, move.from_square, move.to_square)
        bonus = depth * depth
        self.history_heuristic[key] = min(10000, self.history_heuristic.get(key, 0) + bonus)

        if len(self.history_heuristic) > 50000:
            for k in list(self.history_heuristic.keys()):
                self.history_heuristic[k] //= 2
                if self.history_heuristic[k] < 10:
                    del self.history_heuristic[k]

    def _update_killers(self, ply: int, move: chess.Move) -> None:
        killers = self.killer_moves.setdefault(ply, [])
        if move not in killers:
            killers.insert(0, move)
            if len(killers) > 2:
                killers.pop()

    def _hash_key(self, board: chess.Board) -> int:
        try:
            return board._transposition_key()
        except Exception:
            try:
                return board.transposition_key()
            except Exception:
                return hash(board.fen())

    def _extract_pv(self, board: chess.Board) -> List[chess.Move]:
        pv: List[chess.Move] = []
        seen = set()
        for _ in range(20):
            key = self._hash_key(board)
            if key in seen or key not in self.pv_table:
                break
            seen.add(key)
            move = self.pv_table[key]
            if move not in board.legal_moves:
                break
            pv.append(move)
            board.push(move)
        for _ in range(len(pv)):
            board.pop()
        return pv

    def _time_up(self) -> bool:
        if self.stop:
            return True
        if self.max_nodes and self.nodes >= self.max_nodes:
            self.stop = True
            return True
        if self.nodes & 2047 == 0:
            if time.perf_counter() >= self.time_deadline:
                self.stop = True
                return True
        return False


class TTEntry:
    def __init__(self, depth: int, score: int, flag: int, best_move: Optional[chess.Move], age: int) -> None:
        self.depth = depth
        self.score = score
        self.flag = flag
        self.best_move = best_move
        self.age = age
