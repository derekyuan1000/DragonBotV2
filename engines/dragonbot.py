from __future__ import annotations
import time
import random
from typing import Optional, Dict, Tuple, List
import chess
import chess.engine
from engines.eval import evaluate


_last_pv: List[chess.Move] = []
_last_position_fen: Optional[str] = None


def search_alpha_beta(board: chess.Board, time_budget: float, max_depth: int, allowed_root: Optional[List[chess.Move]] = None) -> Tuple[Optional[chess.Move], chess.engine.InfoDict]:
    global _last_pv, _last_position_fen

    INF = 10_000_000
    MATE_SCORE = 1_000_000
    start_time = time.perf_counter()
    nodes = 0
    stop = False
    time_deadline = start_time + max(0.05, time_budget * 0.95)
    tt: Dict[int, Dict[str, object]] = {}
    age = 0
    pv_table: Dict[int, chess.Move] = {}
    killer_moves: Dict[int, List[chess.Move]] = {}
    history_heuristic: Dict[Tuple[bool, int, int], int] = {}
    counter_moves: Dict[Tuple[Optional[int], Optional[int]], chess.Move] = {}

    pv_continuation_depth = 0
    if _last_position_fen is not None and len(_last_pv) >= 2:
        try:
            test_board = chess.Board(_last_position_fen)
            if len(test_board.move_stack) < len(board.move_stack):
                our_move = _last_pv[0]
                expected_opponent_move = _last_pv[1]
                test_board.push(our_move)
                if test_board.fen() == board.fen():
                    print(f"[PV Hit] Opponent played expected move: {expected_opponent_move}")
                    remaining_pv = _last_pv[1:]
                    pv_continuation_depth = len(remaining_pv)
                    print(f"[PV Hit] Continuing from PV with {pv_continuation_depth} moves ahead, boosting depth by {min(pv_continuation_depth, 3)}")
                    max_depth += min(pv_continuation_depth, 3)
        except Exception:
            pass

    def time_up() -> bool:
        nonlocal stop
        if stop:
            return True
        return time.perf_counter() >= time_deadline

    def piece_value(pt: int) -> int:
        return {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}[pt]

    def hash_key(b: chess.Board) -> int:
        try:
            return b._transposition_key()
        except Exception:
            try:
                return b.transposition_key()
            except Exception:
                return hash(b.fen())

    def see(b: chess.Board, m: chess.Move) -> int:
        if not b.is_capture(m):
            return 0
        from_sq = m.from_square
        to_sq = m.to_square
        captured = b.piece_at(to_sq)
        attacker = b.piece_at(from_sq)
        if captured is None or attacker is None:
            return 0
        gain = piece_value(captured.piece_type)
        b.push(m)
        is_attacked = b.is_attacked_by(not b.turn, to_sq)
        b.pop()
        if is_attacked:
            gain -= piece_value(attacker.piece_type)
        return gain

    def update_history(b: chess.Board, m: chess.Move, d: int) -> None:
        key = (b.turn, m.from_square, m.to_square)
        bonus = d * d
        history_heuristic[key] = min(10000, history_heuristic.get(key, 0) + bonus)
        if len(history_heuristic) > 50000:
            for k in list(history_heuristic.keys()):
                history_heuristic[k] //= 2
                if history_heuristic[k] < 10:
                    del history_heuristic[k]

    def update_killers(ply: int, m: chess.Move) -> None:
        ks = killer_moves.setdefault(ply, [])
        if m not in ks:
            ks.insert(0, m)
            if len(ks) > 2:
                ks.pop()

    def ordered_moves(b: chess.Board, tt_move: Optional[chess.Move], ply: int) -> List[chess.Move]:
        mv = list(b.legal_moves)
        killers = killer_moves.get(ply, [])
        killer_set = set(killers)
        prev = b.peek() if len(b.move_stack) > 0 else None
        counter = counter_moves.get((prev.from_square, prev.to_square)) if prev else None
        def score(m: chess.Move) -> int:
            if tt_move and m == tt_move:
                return 10000000
            s = 0
            if b.is_capture(m):
                victim = b.piece_at(m.to_square)
                attacker = b.piece_at(m.from_square)
                if victim and attacker:
                    s += piece_value(victim.piece_type) * 100 - piece_value(attacker.piece_type) + 100000
                    sc = see(b, m)
                    if sc > 0:
                        s += sc
            if m.promotion == chess.QUEEN:
                s += 900000
            elif m.promotion:
                s += 300000
            if b.gives_check(m):
                s += 50000
            if m in killer_set:
                s += 80000
            elif counter and m == counter:
                s += 70000
            s += history_heuristic.get((b.turn, m.from_square, m.to_square), 0)
            return s
        mv.sort(key=score, reverse=True)
        return mv

    def ordered_captures(b: chess.Board) -> List[chess.Move]:
        caps = [m for m in b.legal_moves if b.is_capture(m) or m.promotion == chess.QUEEN]
        def mvv_lva(m: chess.Move) -> int:
            sc = 0
            if b.is_capture(m):
                victim = b.piece_at(m.to_square)
                attacker = b.piece_at(m.from_square)
                if victim and attacker:
                    sc = piece_value(victim.piece_type) * 10 - piece_value(attacker.piece_type)
            if m.promotion == chess.QUEEN:
                sc += 9000
            return sc
        caps.sort(key=mvv_lva, reverse=True)
        return caps

    def extract_pv(b: chess.Board) -> List[chess.Move]:
        pv: List[chess.Move] = []
        seen = set()
        for _ in range(20):
            k = hash_key(b)
            if k in seen or k not in pv_table:
                break
            seen.add(k)
            m = pv_table[k]
            if m not in b.legal_moves:
                break
            pv.append(m)
            b.push(m)
        for _ in range(len(pv)):
            b.pop()
        return pv

    def quiescence(b: chess.Board, alpha: int, beta: int, ply: int) -> int:
        nonlocal nodes
        if time_up():
            return 0
        nodes += 1
        k = hash_key(b)
        e = tt.get(k)
        if e and e["depth"] >= 0:
            tscore = int(e["score"])
            if e["flag"] == 0:
                return tscore
            if e["flag"] == -1 and tscore <= alpha:
                return alpha
            if e["flag"] == 1 and tscore >= beta:
                return beta
        stand_pat = evaluate(b, time_budget)
        if stand_pat >= beta:
            return beta
        BIG_DELTA = 975
        if stand_pat < alpha - BIG_DELTA:
            return alpha
        if alpha < stand_pat:
            alpha = stand_pat
        orig_alpha = alpha
        for m in ordered_captures(b):
            if not b.gives_check(m) and see(b, m) < 0:
                continue
            b.push(m)
            sc = -quiescence(b, -beta, -alpha, ply + 1)
            b.pop()
            if sc >= beta:
                tt[k] = {"depth": 0, "score": beta, "flag": 1, "best": m, "age": age}
                return beta
            if sc > alpha:
                alpha = sc
            if time_up():
                break
        flag = 0 if alpha > orig_alpha else -1
        tt[k] = {"depth": 0, "score": alpha, "flag": flag, "best": None, "age": age}
        return alpha

    def pvs(b: chess.Board, depth: int, alpha: int, beta: int, ply: int, is_pv: bool, allowed: Optional[set[chess.Move]]) -> Tuple[int, Optional[chess.Move]]:
        nonlocal nodes
        if time_up():
            return 0, None
        nodes += 1
        if b.is_checkmate():
            return -MATE_SCORE + ply, None
        if b.is_stalemate() or b.is_insufficient_material():
            return 0, None
        if b.can_claim_threefold_repetition() or b.can_claim_fifty_moves():
            return 0, None
        alpha = max(alpha, -MATE_SCORE + ply)
        beta = min(beta, MATE_SCORE - ply - 1)
        if alpha >= beta:
            return alpha, None
        k = hash_key(b)
        e = tt.get(k)
        tt_move = e["best"] if e else None
        if e and int(e["depth"]) >= depth and not is_pv:
            tscore = int(e["score"])
            if e["flag"] == 0:
                return tscore, tt_move if isinstance(tt_move, chess.Move) else None
            if e["flag"] == -1 and tscore <= alpha:
                return alpha, tt_move if isinstance(tt_move, chess.Move) else None
            if e["flag"] == 1 and tscore >= beta:
                return beta, tt_move if isinstance(tt_move, chess.Move) else None
        if depth <= 0:
            return quiescence(b, alpha, beta, ply), None
        is_check = b.is_check()
        if (not is_pv and not is_check and depth >= 3):
            R = 3 if depth > 6 else 2
            b.push(chess.Move.null())
            s, _ = pvs(b, depth - 1 - R, -beta, -beta + 1, ply + 1, False, allowed)
            s = -s
            b.pop()
            if s >= beta:
                return beta, None
        if is_pv and tt_move is None and depth >= 4:
            _, iid_move = pvs(b, depth - 2, alpha, beta, ply, True, allowed)
            if iid_move:
                tt_move = iid_move
        if depth <= 3 and not is_pv and not is_check and abs(alpha) < MATE_SCORE - 100:
            futility_margin = [0, 200, 350, 500][depth]
            static_eval = evaluate(b, time_budget)
            if static_eval + futility_margin <= alpha:
                return alpha, None
        best_move: Optional[chess.Move] = None
        best_score = -INF
        orig_alpha = alpha
        moves = ordered_moves(b, tt_move if isinstance(tt_move, chess.Move) else None, ply)
        if allowed is not None and ply == 0:
            moves = [m for m in moves if m in allowed]
        if not moves:
            return 0, None
        if is_check:
            depth += 1
        moves_searched = 0
        for m in moves:
            b.push(m)
            do_reduction = False
            reduction = 0
            if (not is_pv and moves_searched >= 4 and depth >= 3 and not is_check and not b.is_check() and not b.is_capture(m) and m.promotion is None):
                reduction = 1
                if moves_searched >= 8:
                    reduction = 2
                if depth > 6:
                    reduction += 1
                do_reduction = True
            if moves_searched == 0:
                sc, _ = pvs(b, depth - 1, -beta, -alpha, ply + 1, is_pv, allowed)
                sc = -sc
            else:
                if do_reduction:
                    sc, _ = pvs(b, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1, False, allowed)
                    sc = -sc
                else:
                    sc = alpha + 1
                if sc > alpha and do_reduction:
                    sc, _ = pvs(b, depth - 1, -alpha - 1, -alpha, ply + 1, False, allowed)
                    sc = -sc
                if sc > alpha and sc < beta:
                    sc, _ = pvs(b, depth - 1, -beta, -alpha, ply + 1, is_pv, allowed)
                    sc = -sc
            b.pop()
            moves_searched += 1
            if sc > best_score:
                best_score = sc
                best_move = m
                if sc > alpha:
                    alpha = sc
                    pv_table[k] = m
                    if alpha >= beta:
                        update_history(b, m, depth)
                        if not b.is_capture(m):
                            update_killers(ply, m)
                            if len(b.move_stack) > 0:
                                prev = b.peek()
                                counter_moves[(prev.from_square, prev.to_square)] = m
                        break
            if time_up():
                break
        flag = 0
        if best_score <= orig_alpha:
            flag = -1
        elif best_score >= beta:
            flag = 1
        tt[k] = {"depth": depth, "score": best_score, "flag": flag, "best": best_move, "age": age}
        return best_score, best_move

    age += 1
    best_move: Optional[chess.Move] = None
    best_score = 0
    pv: List[chess.Move] = []
    last_depth = 0
    allowed_set = set(allowed_root) if isinstance(allowed_root, list) else (allowed_root or None)
    pv_table.clear()
    score, move = pvs(board, 1, -INF, INF, 0, True, allowed_set)
    if move is not None:
        best_move = move
        best_score = score
        pv = extract_pv(board)
    last_depth = 1
    for depth in range(2, max_depth + 1):
        if time_up():
            break
        pv_table.clear()
        alpha = max(-INF, best_score - 50)
        beta = min(INF, best_score + 50)
        score, move = pvs(board, depth, alpha, beta, 0, True, allowed_set)
        if score <= alpha or score >= beta:
            score, move = pvs(board, depth, -INF, INF, 0, True, allowed_set)
        last_depth = depth
        if move is not None:
            best_move = move
            best_score = score
            pv = extract_pv(board)
        if time_up():
            break
        if abs(best_score) > MATE_SCORE - 100:
            break
    time_used = time.perf_counter() - start_time
    legal_moves_list = list(board.legal_moves)
    if best_move is None:
        mv = legal_moves_list if allowed_set is None else [m for m in legal_moves_list if m in allowed_set]
        best_move = random.choice(mv) if mv else None

    _last_pv = pv.copy() if pv else []
    _last_position_fen = board.fen()

    info: chess.engine.InfoDict = {
        "string": "lichess-bot-source:Engine",
        "depth": last_depth,
        "nodes": nodes,
        "nps": int(nodes / max(1e-3, time_used)),
        "pv": pv,
        "score": chess.engine.PovScore(chess.engine.Cp(best_score), board.turn),
    }
    return best_move, info
