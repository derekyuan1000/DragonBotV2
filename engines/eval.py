from __future__ import annotations
from typing import Dict, List, Tuple
import chess


def evaluate(board: chess.Board, time_budget: float) -> int:
    def init_pst() -> Tuple[Dict[int, List[int]], Dict[int, List[int]]]:
        PAWN_MG = [
            0, 0, 0, 0, 0, 0, 0, 0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5, 5, 10, 27, 27, 10, 5, 5,
            0, 0, 0, 25, 25, 0, 0, 0,
            5, -5, -10, 0, 0, -10, -5, 5,
            5, 10, 10, -25, -25, 10, 10, 5,
            0, 0, 0, 0, 0, 0, 0, 0,
        ]
        KNIGHT_MG = [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20, 0, 5, 5, 0, -20, -40,
            -30, 5, 10, 15, 15, 10, 5, -30,
            -30, 0, 15, 20, 20, 15, 0, -30,
            -30, 5, 15, 20, 20, 15, 5, -30,
            -30, 0, 10, 15, 15, 10, 0, -30,
            -40, -20, 0, 0, 0, 0, -20, -40,
            -50, -40, -30, -30, -30, -30, -40, -50,
        ]
        BISHOP_MG = [
            -20, -10, -10, -10, -10, -10, -10, -20,
            -10, 5, 0, 0, 0, 0, 5, -10,
            -10, 10, 10, 10, 10, 10, 10, -10,
            -10, 0, 10, 10, 10, 10, 0, -10,
            -10, 5, 5, 10, 10, 5, 5, -10,
            -10, 0, 5, 10, 10, 5, 0, -10,
            -10, 0, 0, 0, 0, 0, 0, -10,
            -20, -10, -10, -10, -10, -10, -10, -20,
            -20, -10, -10, -10, -10, -10, -10, -20,
        ]
        ROOK_MG = [
            0, 0, 0, 5, 5, 0, 0, 0,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            5, 10, 10, 10, 10, 10, 10, 5,
            0, 0, 0, 0, 0, 0, 0, 0,
        ]
        QUEEN_MG = [
            -20, -10, -10, -5, -5, -10, -10, -20,
            -10, 0, 5, 0, 0, 0, 0, -10,
            -10, 5, 5, 5, 5, 5, 0, -10,
            0, 0, 5, 5, 5, 5, 0, -5,
            -5, 0, 5, 5, 5, 5, 0, -5,
            -10, 0, 5, 5, 5, 5, 0, -10,
            -10, 0, 0, 0, 0, 0, 0, -10,
            -20, -10, -10, -5, -5, -10, -10, -20,
        ]
        KING_MG = [
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -30, -40, -40, -50, -50, -40, -40, -30,
            -20, -30, -30, -40, -40, -30, -30, -20,
            -10, -20, -20, -20, -20, -20, -20, -10,
            20, 20, 0, 0, 0, 0, 20, 20,
            20, 30, 10, 0, 0, 10, 30, 20,
        ]
        PAWN_EG = [
            0, 0, 0, 0, 0, 0, 0, 0,
            80, 80, 80, 80, 80, 80, 80, 80,
            50, 50, 50, 50, 50, 50, 50, 50,
            30, 30, 30, 30, 30, 30, 30, 30,
            20, 20, 20, 20, 20, 20, 20, 20,
            10, 10, 10, 10, 10, 10, 10, 10,
            10, 10, 10, 10, 10, 10, 10, 10,
            0, 0, 0, 0, 0, 0, 0, 0,
        ]
        KNIGHT_EG = [
            -50, -40, -30, -30, -30, -30, -40, -50,
            -40, -20, 0, 0, 0, 0, -20, -40,
            -30, 0, 10, 15, 15, 10, 0, -30,
            -30, 5, 15, 20, 20, 15, 5, -30,
            -30, 0, 15, 20, 20, 15, 0, -30,
            -30, 5, 10, 15, 15, 10, 5, -30,
            -40, -20, 0, 5, 5, 0, -20, -40,
            -50, -40, -30, -30, -30, -30, -40, -50,
        ]
        BISHOP_EG = [
            -20, -10, -10, -10, -10, -10, -10, -20,
            -10, 0, 0, 0, 0, 0, 0, -10,
            -10, 0, 5, 10, 10, 5, 0, -10,
            -10, 5, 5, 10, 10, 5, 5, -10,
            -10, 0, 10, 10, 10, 10, 0, -10,
            -10, 10, 10, 10, 10, 10, 10, -10,
            -10, 5, 0, 0, 0, 0, 5, -10,
            -20, -10, -10, -10, -10, -10, -10, -20,
        ]
        ROOK_EG = [
            0, 0, 0, 0, 0, 0, 0, 0,
            5, 10, 10, 10, 10, 10, 10, 5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            -5, 0, 0, 0, 0, 0, 0, -5,
            0, 0, 0, 5, 5, 0, 0, 0,
        ]
        QUEEN_EG = [
            -20, -10, -10, -5, -5, -10, -10, -20,
            -10, 0, 0, 0, 0, 0, 0, -10,
            -10, 0, 5, 5, 5, 5, 0, -10,
            -5, 0, 5, 5, 5, 5, 0, -5,
            0, 0, 5, 5, 5, 5, 0, -5,
            -10, 5, 5, 5, 5, 5, 0, -10,
            -10, 0, 5, 0, 0, 0, 0, -10,
            -20, -10, -10, -5, -5, -10, -10, -20,
        ]
        KING_EG = [
            -50, -40, -30, -20, -20, -30, -40, -50,
            -30, -20, -10, 0, 0, -10, -20, -30,
            -30, -10, 20, 30, 30, 20, -10, -30,
            -30, -10, 30, 40, 40, 30, -10, -30,
            -30, -10, 30, 40, 40, 30, -10, -30,
            -30, -10, 20, 30, 30, 20, -10, -30,
            -30, -30, 0, 0, 0, 0, -30, -30,
            -50, -30, -30, -30, -30, -30, -30, -50,
        ]
        pst_mg = {
            chess.PAWN: PAWN_MG,
            chess.KNIGHT: KNIGHT_MG,
            chess.BISHOP: BISHOP_MG,
            chess.ROOK: ROOK_MG,
            chess.QUEEN: QUEEN_MG,
            chess.KING: KING_MG,
        }
        pst_eg = {
            chess.PAWN: PAWN_EG,
            chess.KNIGHT: KNIGHT_EG,
            chess.BISHOP: BISHOP_EG,
            chess.ROOK: ROOK_EG,
            chess.QUEEN: QUEEN_EG,
            chess.KING: KING_EG,
        }
        return pst_mg, pst_eg

    if not hasattr(evaluate, "pst_mg"):
        pmg, peg = init_pst()
        setattr(evaluate, "pst_mg", pmg)
        setattr(evaluate, "pst_eg", peg)

    def piece_value(pt: int) -> int:
        return {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }[pt]

    def has_non_pawn_material(color: bool) -> bool:
        for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            if board.pieces(piece_type, color):
                return True
        return False

    def game_phase() -> int:
        total_phase = 24
        phase = total_phase
        phase -= len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
        phase -= len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK))
        phase -= 2 * (len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK)))
        phase -= 4 * (len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK)))
        phase = max(0, phase)
        return (phase * 256 + total_phase // 2) // total_phase

    def evaluate_mobility_simple() -> int:
        s = 0
        for sq in board.piece_map():
            piece = board.piece_at(sq)
            if piece and piece.piece_type != chess.KING:
                sign = 1 if piece.color == chess.WHITE else -1
                attacks = len(board.attacks(sq))
                s += sign * attacks * 2
        return s

    def evaluate_pawns() -> int:
        PASSED_PAWN_BONUS = [0, 10, 20, 40, 60, 90, 130, 0]
        DOUBLED_PAWN_PENALTY = 15
        ISOLATED_PAWN_PENALTY = 20
        s = 0
        for color in [chess.WHITE, chess.BLACK]:
            sign = 1 if color == chess.WHITE else -1
            pawns = board.pieces(chess.PAWN, color)
            for sq in pawns:
                rank = chess.square_rank(sq) if color == chess.WHITE else 7 - chess.square_rank(sq)
                file = chess.square_file(sq)
                is_passed = True
                for r in range(rank + 1, 8):
                    for f_offset in [-1, 0, 1]:
                        check_file = file + f_offset
                        if 0 <= check_file <= 7:
                            check_sq_actual = chess.square(check_file, r if color == chess.WHITE else 7 - r)
                            if check_sq_actual in board.pieces(chess.PAWN, not color):
                                is_passed = False
                                break
                    if not is_passed:
                        break
                if is_passed:
                    s += sign * PASSED_PAWN_BONUS[rank]
            for file in range(8):
                file_pawns = [sq for sq in pawns if chess.square_file(sq) == file]
                if len(file_pawns) >= 2:
                    s -= sign * DOUBLED_PAWN_PENALTY * (len(file_pawns) - 1)
            for sq in pawns:
                file = chess.square_file(sq)
                has_neighbor = False
                for f_offset in [-1, 1]:
                    neighbor_file = file + f_offset
                    if 0 <= neighbor_file <= 7:
                        if any(chess.square_file(p) == neighbor_file for p in pawns):
                            has_neighbor = True
                            break
                if not has_neighbor:
                    s -= sign * ISOLATED_PAWN_PENALTY
        return s

    def evaluate_pieces() -> int:
        ROOK_OPEN_FILE_BONUS = 25
        ROOK_SEMI_OPEN_FILE_BONUS = 15
        BISHOP_PAIR_BONUS = 30
        s = 0
        for color in [chess.WHITE, chess.BLACK]:
            sign = 1 if color == chess.WHITE else -1
            if len(board.pieces(chess.BISHOP, color)) >= 2:
                s += sign * BISHOP_PAIR_BONUS
            for sq in board.pieces(chess.ROOK, color):
                file = chess.square_file(sq)
                our_pawns = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, color))
                their_pawns = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, not color))
                if not our_pawns and not their_pawns:
                    s += sign * ROOK_OPEN_FILE_BONUS
                elif not our_pawns:
                    s += sign * ROOK_SEMI_OPEN_FILE_BONUS
        return s

    def evaluate_king_safety(phase: int) -> int:
        if phase > 200:
            return 0
        KING_SHIELD_BONUS = 8
        KING_ATTACK_WEIGHT = 10
        s = 0
        for color in [chess.WHITE, chess.BLACK]:
            sign = 1 if color == chess.WHITE else -1
            ksq = board.king(color)
            if ksq is None:
                continue
            rank_dir = 1 if color == chess.WHITE else -1
            shield_rank = chess.square_rank(ksq) + rank_dir
            if 0 <= shield_rank <= 7:
                for file_offset in [-1, 0, 1]:
                    shield_file = chess.square_file(ksq) + file_offset
                    if 0 <= shield_file <= 7:
                        shield_sq = chess.square(shield_file, shield_rank)
                        if shield_sq in board.pieces(chess.PAWN, color):
                            s += sign * KING_SHIELD_BONUS
            attack_count = 0
            king_zone = [ksq]
            for offset in [-9, -8, -7, -1, 1, 7, 8, 9]:
                sq = ksq + offset
                if 0 <= sq <= 63 and abs(chess.square_file(ksq) - chess.square_file(sq)) <= 1:
                    king_zone.append(sq)
            for sq in king_zone:
                if board.is_attacked_by(not color, sq):
                    attack_count += 1
            s -= sign * attack_count * KING_ATTACK_WEIGHT
        return s

    if board.is_checkmate():
        return -1000000 + len(board.move_stack)
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    phase = game_phase()
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1
        for piece_type in chess.PIECE_TYPES:
            for sq in board.pieces(piece_type, color):
                base_value = piece_value(piece_type)
                sq_normalized = sq if color == chess.WHITE else chess.square_mirror(sq)
                mg_bonus = getattr(evaluate, "pst_mg")[piece_type][sq_normalized]
                eg_bonus = getattr(evaluate, "pst_eg")[piece_type][sq_normalized]
                pos_bonus = ((mg_bonus * (256 - phase)) + (eg_bonus * phase)) // 256
                score += sign * (base_value + pos_bonus)
    score += evaluate_pawns()
    score += evaluate_pieces()
    score += evaluate_king_safety(phase)
    if time_budget >= 0.5:
        score += evaluate_mobility_simple()
    return score if board.turn == chess.WHITE else -score
