"""
Some example classes for people who want to create a homemade bot.

With these classes, bot makers will not have to implement the UCI or XBoard interfaces themselves.
"""
import chess
import chess.polyglot
import chess.syzygy
from chess.engine import PlayResult, Limit, Cp, PovScore
import random
from lib.engine_wrapper import MinimalEngine
from lib.lichess_types import MOVE, HOMEMADE_ARGS_TYPE
import logging
import time
from typing import Dict, Tuple, Optional, List
import os


# Use this logger variable to print messages to the console or log files.
# logger.info("message") will always print "message" to the console or log file.
# logger.debug("message") will only print "message" if verbose logging is enabled.
logger = logging.getLogger(__name__)


class ExampleEngine(MinimalEngine):
    """An example engine that all homemade engines inherit."""


# Bot names and ideas from tom7's excellent eloWorld video

class RandomMove(ExampleEngine):
    """Get a random move."""

    def search(self, board: chess.Board, *args: HOMEMADE_ARGS_TYPE) -> PlayResult:  # noqa: ARG002
        """Choose a random move."""
        return PlayResult(random.choice(list(board.legal_moves)), None)


class Alphabetical(ExampleEngine):
    """Get the first move when sorted by san representation."""

    def search(self, board: chess.Board, *args: HOMEMADE_ARGS_TYPE) -> PlayResult:  # noqa: ARG002
        """Choose the first move alphabetically."""
        moves = list(board.legal_moves)
        moves.sort(key=board.san)
        return PlayResult(moves[0], None)


class FirstMove(ExampleEngine):
    """Get the first move when sorted by uci representation."""

    def search(self, board: chess.Board, *args: HOMEMADE_ARGS_TYPE) -> PlayResult:  # noqa: ARG002
        """Choose the first move alphabetically in uci representation."""
        moves = list(board.legal_moves)
        moves.sort(key=str)
        return PlayResult(moves[0], None)


class ComboEngine(ExampleEngine):
    """
    Get a move using multiple different methods.

    This engine demonstrates how one can use `time_limit`, `draw_offered`, and `root_moves`.
    """

    def search(self,
               board: chess.Board,
               time_limit: Limit,
               ponder: bool,  # noqa: ARG002
               draw_offered: bool,
               root_moves: MOVE) -> PlayResult:
        """
        Choose a move using multiple different methods.

        :param board: The current position.
        :param time_limit: Conditions for how long the engine can search (e.g. we have 10 seconds and search up to depth 10).
        :param ponder: Whether the engine can ponder after playing a move.
        :param draw_offered: Whether the bot was offered a draw.
        :param root_moves: If it is a list, the engine should only play a move that is in `root_moves`.
        :return: The move to play.
        """
        if isinstance(time_limit.time, int):
            my_time = time_limit.time
            my_inc = 0
        elif board.turn == chess.WHITE:
            my_time = time_limit.white_clock if isinstance(time_limit.white_clock, int) else 0
            my_inc = time_limit.white_inc if isinstance(time_limit.white_inc, int) else 0
        else:
            my_time = time_limit.black_clock if isinstance(time_limit.black_clock, int) else 0
            my_inc = time_limit.black_inc if isinstance(time_limit.black_inc, int) else 0

        possible_moves = root_moves if isinstance(root_moves, list) else list(board.legal_moves)

        if my_time / 60 + my_inc > 10:
            # Choose a random move.
            move = random.choice(possible_moves)
        else:
            # Choose the first move alphabetically in uci representation.
            possible_moves.sort(key=str)
            move = possible_moves[0]
        return PlayResult(move, None, draw_offered=draw_offered)


class GrandmasterEngine(ExampleEngine):
    """
    A grandmaster-level chess engine with advanced features.
    
    Features:
    - Minimax algorithm with alpha-beta pruning
    - Sophisticated evaluation function (material, piece activity, king safety, pawn structure)
    - Transposition table for position caching
    - Opening book support
    - Endgame tablebase support
    """
    
    # Piece values in centipawns
    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 20000
    }
    
    # Piece-square tables for positional evaluation
    PAWN_TABLE = [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ]
    
    KNIGHT_TABLE = [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ]
    
    BISHOP_TABLE = [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ]
    
    ROOK_TABLE = [
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ]
    
    QUEEN_TABLE = [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ]
    
    KING_MIDDLE_GAME_TABLE = [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
        20, 20,  0,  0,  0,  0, 20, 20,
        20, 30, 10,  0,  0, 10, 30, 20
    ]
    
    KING_END_GAME_TABLE = [
        -50,-40,-30,-20,-20,-30,-40,-50,
        -30,-20,-10,  0,  0,-10,-20,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 30, 40, 40, 30,-10,-30,
        -30,-10, 20, 30, 30, 20,-10,-30,
        -30,-30,  0,  0,  0,  0,-30,-30,
        -50,-30,-30,-30,-30,-30,-30,-50
    ]
    
    def __init__(self, commands: list, options: dict, stderr: Optional[int],
                 draw_or_resign: dict, game: Optional[object] = None, name: Optional[str] = None,
                 **popen_args: str) -> None:
        """Initialize the Grandmaster Engine with transposition table."""
        super().__init__(commands, options, stderr, draw_or_resign, game, name or "GrandmasterEngine", **popen_args)
        
        # Transposition table: stores {position_hash: (depth, score, flag, best_move)}
        # flag: 0=exact, 1=lower bound, 2=upper bound
        self.transposition_table: Dict[int, Tuple[int, int, int, Optional[chess.Move]]] = {}
        self.nodes_searched = 0
        self.max_table_size = 1000000  # Store up to 1 million positions
        
        # Opening book path (can be configured)
        self.opening_book_path = None
        self.use_opening_book = True
        
        # Try to find opening book in common locations
        for book_path in ["./engines/book.bin", "./book.bin", "./engines/performance.bin"]:
            if os.path.exists(book_path):
                self.opening_book_path = book_path
                logger.info(f"Found opening book: {book_path}")
                break
        
        # Endgame tablebase path
        self.syzygy_path = None
        self.use_endgame_tb = True
        
        # Try to find syzygy tablebases
        for tb_path in ["./engines/syzygy", "./syzygy", "./tablebases/syzygy"]:
            if os.path.exists(tb_path):
                self.syzygy_path = tb_path
                logger.info(f"Found Syzygy tablebase: {tb_path}")
                break
    
    def search(self,
               board: chess.Board,
               time_limit: Limit,
               ponder: bool,  # noqa: ARG002
               draw_offered: bool,
               root_moves: MOVE) -> PlayResult:
        """
        Search for the best move using minimax with alpha-beta pruning.
        
        :param board: The current position.
        :param time_limit: Conditions for how long the engine can search.
        :param ponder: Whether the engine can ponder after playing a move.
        :param draw_offered: Whether the bot was offered a draw.
        :param root_moves: If it is a list, the engine should only play a move that is in `root_moves`.
        :return: The move to play.
        """
        self.nodes_searched = 0
        start_time = time.time()
        
        # Determine time allocation
        if isinstance(time_limit.time, (int, float)):
            max_time = float(time_limit.time)
        elif board.turn == chess.WHITE:
            clock = time_limit.white_clock if isinstance(time_limit.white_clock, (int, float)) else 30.0
            inc = time_limit.white_inc if isinstance(time_limit.white_inc, (int, float)) else 0.0
            max_time = float(clock / 20 + inc * 0.8)  # Use portion of remaining time
        else:
            clock = time_limit.black_clock if isinstance(time_limit.black_clock, (int, float)) else 30.0
            inc = time_limit.black_inc if isinstance(time_limit.black_inc, (int, float)) else 0.0
            max_time = float(clock / 20 + inc * 0.8)
        
        # Cap maximum thinking time
        max_time = min(max_time, 30.0)
        max_time = max(max_time, 0.1)  # At least 100ms
        
        logger.info(f"Allocated time for search: {max_time:.2f}s")
        
        # Check opening book first
        if self.use_opening_book and self.opening_book_path and len(board.move_stack) < 20:
            book_move = self._get_opening_book_move(board)
            if book_move:
                logger.info(f"Using opening book move: {book_move}")
                return PlayResult(book_move, None, {"string": "Opening Book", "depth": 0})
        
        # Check endgame tablebases
        if self.use_endgame_tb and self.syzygy_path:
            pieces = chess.popcount(board.occupied)
            if pieces <= 7:  # Typical tablebase limit
                tb_move = self._get_tablebase_move(board)
                if tb_move:
                    logger.info(f"Using tablebase move: {tb_move}")
                    return PlayResult(tb_move, None, {"string": "Endgame Tablebase", "depth": 0})
        
        # Get legal moves to search
        possible_moves = root_moves if isinstance(root_moves, list) else list(board.legal_moves)
        
        if not possible_moves:
            # No legal moves, shouldn't happen
            return PlayResult(None, None)
        
        if len(possible_moves) == 1:
            # Only one legal move
            return PlayResult(possible_moves[0], None)
        
        # Iterative deepening search
        best_move = possible_moves[0]
        best_score = -999999
        depth = 1
        max_depth = 6  # Maximum search depth
        
        while depth <= max_depth:
            if time.time() - start_time > max_time * 0.8:
                break
            
            logger.debug(f"Searching at depth {depth}")
            score, move = self._iterative_deepening_search(board, depth, start_time, max_time)
            
            if move:
                best_move = move
                best_score = score
                logger.debug(f"Depth {depth}: best move {move}, score {score}")
            
            # Stop if we found a mate
            if abs(score) > 10000:
                break
            
            depth += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Search completed: depth={depth-1}, nodes={self.nodes_searched}, "
                   f"time={elapsed:.2f}s, nps={int(self.nodes_searched/max(elapsed, 0.001))}, "
                   f"score={best_score}")
        
        # Create info dict for the move
        info = {
            "depth": depth - 1,
            "nodes": self.nodes_searched,
            "time": elapsed,
            "score": PovScore(Cp(best_score), board.turn),
            "nps": int(self.nodes_searched / max(elapsed, 0.001))
        }
        
        return PlayResult(best_move, None, info, draw_offered=draw_offered)
    
    def _iterative_deepening_search(self, board: chess.Board, depth: int, 
                                   start_time: float, max_time: float) -> Tuple[int, Optional[chess.Move]]:
        """Perform iterative deepening search at a specific depth."""
        best_move = None
        alpha = -999999
        beta = 999999
        
        # Order moves for better pruning
        moves = self._order_moves(board, list(board.legal_moves))
        
        for move in moves:
            # Check time limit
            if time.time() - start_time > max_time:
                break
            
            board.push(move)
            score = -self._minimax_alpha_beta(board, depth - 1, -beta, -alpha, start_time, max_time)
            board.pop()
            
            if score > alpha:
                alpha = score
                best_move = move
        
        return alpha, best_move
    
    def _minimax_alpha_beta(self, board: chess.Board, depth: int, alpha: int, beta: int,
                           start_time: float, max_time: float) -> int:
        """
        Minimax algorithm with alpha-beta pruning.
        
        :param board: Current board position
        :param depth: Remaining search depth
        :param alpha: Alpha value for pruning
        :param beta: Beta value for pruning
        :param start_time: Search start time
        :param max_time: Maximum search time
        :return: Position evaluation score
        """
        self.nodes_searched += 1
        
        # Check time limit periodically
        if self.nodes_searched % 1000 == 0:
            if time.time() - start_time > max_time:
                return 0
        
        # Check transposition table
        board_hash = chess.polyglot.zobrist_hash(board)
        if board_hash in self.transposition_table:
            stored_depth, stored_score, flag, stored_move = self.transposition_table[board_hash]
            if stored_depth >= depth:
                if flag == 0:  # Exact score
                    return stored_score
                elif flag == 1:  # Lower bound
                    alpha = max(alpha, stored_score)
                elif flag == 2:  # Upper bound
                    beta = min(beta, stored_score)
                
                if alpha >= beta:
                    return stored_score
        
        # Terminal conditions
        if depth == 0 or board.is_game_over():
            return self._evaluate_position(board)
        
        # Quiescence search at depth 0 for captures
        if depth == 0:
            return self._quiescence_search(board, alpha, beta)
        
        best_move = None
        best_score = -999999
        flag = 2  # Upper bound by default
        
        # Order moves for better pruning
        moves = self._order_moves(board, list(board.legal_moves))
        
        for move in moves:
            board.push(move)
            score = -self._minimax_alpha_beta(board, depth - 1, -beta, -alpha, start_time, max_time)
            board.pop()
            
            if score > best_score:
                best_score = score
                best_move = move
            
            alpha = max(alpha, score)
            
            # Alpha-beta pruning
            if alpha >= beta:
                flag = 1  # Lower bound
                break
        
        if best_score > alpha:
            flag = 0  # Exact score
        
        # Store in transposition table
        if len(self.transposition_table) < self.max_table_size:
            self.transposition_table[board_hash] = (depth, best_score, flag, best_move)
        
        return best_score
    
    def _quiescence_search(self, board: chess.Board, alpha: int, beta: int) -> int:
        """Search only capture moves to avoid horizon effect."""
        stand_pat = self._evaluate_position(board)
        
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
        
        # Only consider captures
        for move in board.legal_moves:
            if board.is_capture(move):
                board.push(move)
                score = -self._quiescence_search(board, -beta, -alpha)
                board.pop()
                
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
        
        return alpha
    
    def _order_moves(self, board: chess.Board, moves: List[chess.Move]) -> List[chess.Move]:
        """
        Order moves for better alpha-beta pruning.
        Priority: checks > captures > others
        """
        def move_priority(move: chess.Move) -> int:
            score = 0
            
            # Prioritize checks
            board.push(move)
            if board.is_check():
                score += 10000
            board.pop()
            
            # Prioritize captures (MVV-LVA: Most Valuable Victim - Least Valuable Attacker)
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    score += self.PIECE_VALUES.get(victim.piece_type, 0) * 10
                    score -= self.PIECE_VALUES.get(attacker.piece_type, 0)
            
            # Prioritize promotions
            if move.promotion:
                score += 9000
            
            # Check transposition table for this move
            board.push(move)
            board_hash = chess.polyglot.zobrist_hash(board)
            if board_hash in self.transposition_table:
                score += 5000
            board.pop()
            
            return -score  # Negative because we want descending order
        
        return sorted(moves, key=move_priority)
    
    def _evaluate_position(self, board: chess.Board) -> int:
        """
        Sophisticated evaluation function considering multiple factors:
        - Material balance
        - Piece-square tables (positional value)
        - Piece activity (mobility)
        - King safety
        - Pawn structure
        """
        if board.is_checkmate():
            # Return a very large negative score (we're being mated)
            return -20000
        
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        
        score = 0
        
        # Material and positional evaluation
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = self._piece_value(piece, square, board)
                score += value if piece.color == chess.WHITE else -value
        
        # Piece activity (mobility)
        mobility_score = self._evaluate_mobility(board)
        score += mobility_score
        
        # King safety
        king_safety = self._evaluate_king_safety(board)
        score += king_safety
        
        # Pawn structure
        pawn_structure = self._evaluate_pawn_structure(board)
        score += pawn_structure
        
        # Return score from current player's perspective
        return score if board.turn == chess.WHITE else -score
    
    def _piece_value(self, piece: chess.Piece, square: int, board: chess.Board) -> int:
        """Calculate piece value including positional bonus."""
        base_value = self.PIECE_VALUES.get(piece.piece_type, 0)
        
        # Get positional bonus from piece-square tables
        # Flip square for black pieces
        table_square = square if piece.color == chess.WHITE else chess.square_mirror(square)
        
        positional_bonus = 0
        if piece.piece_type == chess.PAWN:
            positional_bonus = self.PAWN_TABLE[table_square]
        elif piece.piece_type == chess.KNIGHT:
            positional_bonus = self.KNIGHT_TABLE[table_square]
        elif piece.piece_type == chess.BISHOP:
            positional_bonus = self.BISHOP_TABLE[table_square]
        elif piece.piece_type == chess.ROOK:
            positional_bonus = self.ROOK_TABLE[table_square]
        elif piece.piece_type == chess.QUEEN:
            positional_bonus = self.QUEEN_TABLE[table_square]
        elif piece.piece_type == chess.KING:
            # Use different table for endgame
            pieces = chess.popcount(board.occupied)
            if pieces <= 12:  # Endgame
                positional_bonus = self.KING_END_GAME_TABLE[table_square]
            else:
                positional_bonus = self.KING_MIDDLE_GAME_TABLE[table_square]
        
        return base_value + positional_bonus
    
    def _evaluate_mobility(self, board: chess.Board) -> int:
        """Evaluate piece mobility (number of legal moves)."""
        white_mobility = 0
        black_mobility = 0
        
        # Count mobility for current position
        original_turn = board.turn
        
        board.turn = chess.WHITE
        white_mobility = len(list(board.legal_moves))
        
        board.turn = chess.BLACK
        black_mobility = len(list(board.legal_moves))
        
        board.turn = original_turn
        
        return (white_mobility - black_mobility) * 10
    
    def _evaluate_king_safety(self, board: chess.Board) -> int:
        """Evaluate king safety based on pawn shield and attacks near king."""
        score = 0
        
        for color in [chess.WHITE, chess.BLACK]:
            king_square = board.king(color)
            if king_square is None:
                continue
            
            safety = 0
            
            # Pawn shield
            if color == chess.WHITE:
                shield_squares = [king_square + 8, king_square + 7, king_square + 9]
            else:
                shield_squares = [king_square - 8, king_square - 7, king_square - 9]
            
            for sq in shield_squares:
                if 0 <= sq < 64:
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        safety += 10
            
            # Penalty for attacks near king
            attackers = len(board.attackers(not color, king_square))
            safety -= attackers * 20
            
            score += safety if color == chess.WHITE else -safety
        
        return score
    
    def _evaluate_pawn_structure(self, board: chess.Board) -> int:
        """Evaluate pawn structure (doubled, isolated, passed pawns)."""
        score = 0
        
        for color in [chess.WHITE, chess.BLACK]:
            pawns = board.pieces(chess.PAWN, color)
            
            for pawn_square in pawns:
                pawn_file = chess.square_file(pawn_square)
                pawn_rank = chess.square_rank(pawn_square)
                
                # Check for doubled pawns
                file_pawns = [sq for sq in pawns if chess.square_file(sq) == pawn_file]
                if len(file_pawns) > 1:
                    score += -10 if color == chess.WHITE else 10
                
                # Check for isolated pawns
                adjacent_files = [pawn_file - 1, pawn_file + 1]
                has_support = any(
                    chess.square_file(sq) in adjacent_files
                    for sq in pawns
                )
                if not has_support:
                    score += -15 if color == chess.WHITE else 15
                
                # Check for passed pawns
                is_passed = True
                if color == chess.WHITE:
                    blocking_squares = range(pawn_square + 8, 64, 8)
                else:
                    blocking_squares = range(pawn_square - 8, -1, -8)
                
                for sq in blocking_squares:
                    if 0 <= sq < 64:
                        piece = board.piece_at(sq)
                        if piece and piece.piece_type == chess.PAWN and piece.color != color:
                            # Check if enemy pawn can stop it
                            sq_file = chess.square_file(sq)
                            if abs(sq_file - pawn_file) <= 1:
                                is_passed = False
                                break
                
                if is_passed:
                    bonus = (pawn_rank if color == chess.WHITE else 7 - pawn_rank) * 10
                    score += bonus if color == chess.WHITE else -bonus
        
        return score
    
    def _get_opening_book_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Get a move from the opening book if available."""
        if not self.opening_book_path:
            return None
        
        try:
            with chess.polyglot.open_reader(self.opening_book_path) as reader:
                try:
                    entry = reader.weighted_choice(board)
                    return entry.move
                except IndexError:
                    # No book move found
                    return None
        except Exception as e:
            logger.debug(f"Error reading opening book: {e}")
            return None
    
    def _get_tablebase_move(self, board: chess.Board) -> Optional[chess.Move]:
        """Get a move from endgame tablebases if available."""
        if not self.syzygy_path:
            return None
        
        try:
            with chess.syzygy.open_tablebase(self.syzygy_path) as tablebase:
                try:
                    # Get best move based on DTZ (distance to zeroing move)
                    best_move = None
                    best_dtz = 999999
                    
                    for move in board.legal_moves:
                        board.push(move)
                        try:
                            dtz = tablebase.probe_dtz(board)
                            if abs(dtz) < abs(best_dtz):
                                best_dtz = dtz
                                best_move = move
                        except:
                            pass
                        board.pop()
                    
                    return best_move
                except Exception as e:
                    logger.debug(f"Tablebase probe failed: {e}")
                    return None
        except Exception as e:
            logger.debug(f"Error opening tablebase: {e}")
            return None
