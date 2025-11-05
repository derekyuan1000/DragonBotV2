from typing import Tuple
import chess
import chess.engine


class TimeManager:
    def __init__(self):
        self.opening_time_factor = 0.05
        self.middlegame_time_factor = 0.1
        self.endgame_time_factor = 0.12
        self.increment_usage_factor = 0.8
        self.position_complexity_weight = 1.0

    def evaluate_position_complexity(self, board: chess.Board) -> float:
        complexity = 0.0

        legal_moves = list(board.legal_moves)
        num_legal_moves = len(legal_moves)

        complexity += num_legal_moves * 0.5

        capture_count = sum(1 for m in legal_moves if board.is_capture(m))
        complexity += capture_count * 1.5

        if board.is_check():
            complexity += 8.0

        check_count = sum(1 for m in legal_moves if board.gives_check(m))
        complexity += check_count * 1.0

        promotion_count = sum(1 for m in legal_moves if m.promotion)
        complexity += promotion_count * 2.0

        central_control = 0
        center_squares = [chess.E4, chess.D4, chess.E5, chess.D5]
        for sq in center_squares:
            if board.is_attacked_by(chess.WHITE, sq):
                central_control += 1
            if board.is_attacked_by(chess.BLACK, sq):
                central_control += 1
        complexity += central_control * 0.3

        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
        rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
        complexity += (queens * 2.0 + rooks * 1.0)

        pawns = len(board.pieces(chess.PAWN, chess.WHITE)) + len(board.pieces(chess.PAWN, chess.BLACK))
        if pawns < 8:
            complexity += (8 - pawns) * 0.5

        return complexity

    def calculate_game_phase(self, board: chess.Board) -> str:
        piece_count = len(board.piece_map())
        move_count = len(board.move_stack)

        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
        rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))

        if move_count < 20:
            return "opening"
        elif piece_count <= 12 or (queens == 0 and rooks <= 2):
            return "endgame"
        else:
            return "middlegame"

    def calculate_time_allocation(self, board: chess.Board, time_limit: chess.engine.Limit, max_depth: int) -> Tuple[float, int]:
        if not time_limit:
            return 1.0, 10

        if hasattr(time_limit, 'white_clock') and time_limit.white_clock is not None:
            if board.turn == chess.WHITE:
                remaining_time = float(time_limit.white_clock)
                increment = float(time_limit.white_inc or 0.0)
            else:
                remaining_time = float(time_limit.black_clock)
                increment = float(time_limit.black_inc or 0.0)
        elif time_limit.time is not None:
            remaining_time = float(time_limit.time)
            increment = float(getattr(time_limit, 'increment', 0.0) or getattr(time_limit, 'inc', 0.0) or 0.0)
        else:
            return 1.0, 10

        game_phase = self.calculate_game_phase(board)

        if game_phase == "opening":
            time_factor = self.opening_time_factor
            base_depth = 7
        elif game_phase == "middlegame":
            time_factor = self.middlegame_time_factor
            base_depth = 9
        else:
            time_factor = self.endgame_time_factor
            base_depth = 6

        complexity = self.evaluate_position_complexity(board)
        complexity_normalized = min(complexity / 30.0, 2.0)

        adjusted_time_factor = time_factor * (1.0 + complexity_normalized * self.position_complexity_weight)

        move_count = len(board.move_stack)
        expected_remaining_moves = max(20, 60 - move_count)

        time_ratio = remaining_time / (remaining_time + increment * expected_remaining_moves)
        allocated_time = (remaining_time / expected_remaining_moves) * (1.0 + adjusted_time_factor) * time_ratio
        allocated_time += increment * self.increment_usage_factor

        if remaining_time > 300:
            cap_percentage = 0.4
        elif remaining_time > 120:
            cap_percentage = 0.35
        elif remaining_time > 30:
            cap_percentage = 0.3
        else:
            cap_percentage = 0.25

        allocated_time = min(allocated_time, remaining_time * cap_percentage)
        allocated_time = max(allocated_time, 0.05)

        depth_from_time = base_depth
        if allocated_time > 10.0:
            depth_from_time = base_depth + 8
        elif allocated_time > 5.0:
            depth_from_time = base_depth + 6
        elif allocated_time > 2.0:
            depth_from_time = base_depth + 5
        elif allocated_time > 1.0:
            depth_from_time = base_depth + 4
        elif allocated_time > 0.5:
            depth_from_time = base_depth + 3

        complexity_depth_bonus = int(complexity_normalized * 3)
        target_depth = min(depth_from_time + complexity_depth_bonus, max_depth)
        return allocated_time, target_depth
