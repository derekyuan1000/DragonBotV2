from __future__ import annotations
import os
import csv
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple
import chess
import chess.polyglot
import chess.syzygy


@dataclass
class Opening:
    eco_code: str
    name: str
    moves: List[chess.Move]


class OpeningsMixin:
    def _open_tb(self) -> None:
        if getattr(self, "tb", None):
            try:
                self.tb.close()
            except Exception:
                pass
            self.tb = None
        if getattr(self, "tb_paths", None):
            try:
                tb = chess.syzygy.open_tablebase(self.tb_paths[0])
                for p in self.tb_paths[1:]:
                    tb.add_directory(p)
                self.tb = tb
            except Exception:
                self.tb = None

    def _load_csv_openings(self) -> None:
        self.csv_openings = []
        path = self.csv_opening_path
        candidate_paths = [path]
        if not os.path.isabs(path):
            candidate_paths.append(os.path.normpath(os.path.join(os.getcwd(), path)))
            candidate_paths.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", path)))
        if os.path.basename(path).lower() == "openings.csv":
            dir_part = os.path.dirname(path) or "."
            candidate_paths.append(os.path.join(dir_part, "openings.csv"))
            if not os.path.isabs(path):
                candidate_paths.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", dir_part, "openings.csv")))
        for p in candidate_paths:
            if not os.path.exists(p):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        eco = (row.get("ECO Code") or "").strip()
                        name = (row.get("Name") or "").strip()
                        moves_str = (row.get("Opening Moves") or "").strip()
                        if not moves_str:
                            continue
                        board = chess.Board()
                        parsed_moves: List[chess.Move] = []
                        tokens = moves_str.replace(".", " ").split()
                        for tok in tokens:
                            if tok.isdigit():
                                continue
                            try:
                                mv = board.parse_san(tok)
                                parsed_moves.append(mv)
                                board.push(mv)
                            except Exception:
                                continue
                        if parsed_moves:
                            self.csv_openings.append(Opening(eco_code=eco, name=name or eco or "Opening", moves=parsed_moves))
                if self.csv_openings:
                    break
            except Exception:
                continue

    def _find_csv_opening_move(self, board: chess.Board) -> Optional[Tuple[chess.Move, str]]:
        if not getattr(self, "use_csv_openings", False) or not getattr(self, "csv_openings", []):
            return None
        current_moves = list(board.move_stack)
        ply = len(current_moves)
        candidates: List[Tuple[chess.Move, str]] = []
        for op in self.csv_openings:
            if ply >= len(op.moves):
                continue
            match = True
            for i, m in enumerate(current_moves):
                if i >= len(op.moves) or m != op.moves[i]:
                    match = False
                    break
            if not match:
                continue
            next_move = op.moves[ply]
            if next_move in board.legal_moves:
                candidates.append((next_move, op.name))
        if not candidates:
            return None
        return random.choice(candidates)

    def _tb_in_range(self, board: chess.Board) -> bool:
        return chess.popcount(board.occupied) <= getattr(self, "tb_probe_limit", 7) and board.uci_variant == "chess"

    def _tb_best_move(self, board: chess.Board) -> Optional[chess.Move]:
        try:
            assert getattr(self, "tb", None) is not None
            best = None
            best_wdl = -999
            for m in board.legal_moves:
                board.push(m)
                try:
                    wdl = -self.tb.probe_wdl(board)
                except Exception:
                    wdl = -999
                board.pop()
                if wdl > best_wdl:
                    best_wdl = wdl
                    best = m
            return best
        except Exception:
            return None

    def _book_move(self, board: chess.Board) -> Optional[chess.Move]:
        for path in getattr(self, "book_paths", []):
            try:
                with chess.polyglot.open_reader(path) as reader:
                    entries = list(reader.find_all(board))
                    entries = [e for e in entries if e.weight >= getattr(self, "book_min_weight", 1)]
                    if not entries:
                        continue
                    if getattr(self, "randomize_book", True):
                        weights = [e.weight for e in entries]
                        total = sum(weights)
                        r = random.uniform(0, total)
                        upto = 0
                        for e in entries:
                            if upto + e.weight >= r:
                                return e.move
                            upto += e.weight
                    return max(entries, key=lambda e: e.weight).move
            except Exception:
                continue
        return None

