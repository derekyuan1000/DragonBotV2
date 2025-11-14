from typing import Tuple
import chess
import chess.engine


def estimate_moves_remaining(board: chess.Board) -> int:
    move_number = board.fullmove_number
    piece_count = len(board.piece_map())

    if move_number < 10:
        base_remaining = 35
    elif move_number < 20:
        base_remaining = 30
    elif move_number < 30:
        base_remaining = 25
    else:
        base_remaining = max(15, 50 - move_number)

    if piece_count <= 6:
        base_remaining = min(base_remaining, 15)
    elif piece_count <= 10:
        base_remaining = min(base_remaining, 20)
    elif piece_count <= 16:
        base_remaining = min(base_remaining, 25)

    return max(10, base_remaining)


def calculate_position_complexity(board: chess.Board) -> float:
    complexity_score = 1.0

    legal_moves_count = board.legal_moves.count()
    if legal_moves_count > 35:
        complexity_score += 0.4
    elif legal_moves_count > 25:
        complexity_score += 0.2
    elif legal_moves_count < 10:
        complexity_score -= 0.2

    if board.is_check():
        complexity_score += 0.3


    piece_count = len(board.piece_map())
    if piece_count > 20:
        complexity_score += 0.2
    elif piece_count < 10:
        complexity_score -= 0.1

    captures = [move for move in board.legal_moves if board.is_capture(move)]
    if len(captures) > 5:
        complexity_score += 0.2

    pawns = board.pieces(chess.PAWN, board.turn)
    if len(pawns) >= 4:
        complexity_score += 0.1

    return max(0.5, min(2.0, complexity_score))


def calculate_time_allocation(board: chess.Board, time_limit: chess.engine.Limit, max_depth: int) -> Tuple[float, int]:
    default_time = 1.0
    default_depth = max_depth

    our_color = board.turn

    if our_color == chess.WHITE:
        remaining_time = getattr(time_limit, 'white_clock', None)
        increment = getattr(time_limit, 'white_inc', None) or 0
    else:
        remaining_time = getattr(time_limit, 'black_clock', None)
        increment = getattr(time_limit, 'black_inc', None) or 0

    movetime = getattr(time_limit, 'time', None)
    if movetime is not None:
        allocated_time = movetime
        if allocated_time < 0.5:
            adaptive_depth = max(2, max_depth - 5)
        elif allocated_time < 2.0:
            adaptive_depth = max(3, max_depth - 3)
        else:
            adaptive_depth = max_depth
        return (allocated_time, adaptive_depth)

    if remaining_time is None:
        return (default_time, default_depth)

    moves_remaining = estimate_moves_remaining(board)

    complexity = calculate_position_complexity(board)

    emergency_reserve = min(remaining_time * 0.1, 2.0)
    usable_time = max(0, remaining_time - emergency_reserve)

    base_time_per_move = usable_time / moves_remaining

    base_time_per_move += increment * 0.5

    allocated_time = base_time_per_move * complexity

    if remaining_time < 10:
        allocated_time = min(allocated_time, remaining_time * 0.15)
    elif remaining_time < 30:
        allocated_time = min(allocated_time, remaining_time * 0.25)

    if board.fullmove_number <= 6 and complexity < 1.2:
        allocated_time *= 0.6

    if board.is_check() or complexity > 1.5:
        allocated_time *= 1.3

    allocated_time = max(0.1, min(allocated_time, remaining_time - 0.5))

    if allocated_time < 0.5:
        adaptive_depth = max(3, int(max_depth * 0.5))
    elif allocated_time < 1.0:
        adaptive_depth = max(5, int(max_depth * 0.7))
    elif allocated_time < 3.0:
        adaptive_depth = max(7, int(max_depth * 0.85))
    else:
        adaptive_depth = max_depth

    if complexity > 1.5 and allocated_time > 2.0:
        adaptive_depth = max_depth

    piece_count = len(board.piece_map())
    if piece_count <= 8 and allocated_time > 1.0:
        adaptive_depth = min(max_depth, max_depth)

    print(f"[Time Manager] Target Time: {allocated_time:.2f}s | Target Depth: {adaptive_depth} | Complexity: {complexity:.2f} | Moves Remaining: {moves_remaining}")

    return (allocated_time, adaptive_depth)
