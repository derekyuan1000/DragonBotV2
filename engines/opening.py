from __future__ import annotations
import os
import csv
import random
from typing import List, Optional, Tuple, Dict, Any
import chess
import chess.engine
import chess.polyglot
import chess.syzygy


def opening_move(board: chess.Board, options: Dict[str, Any] | None = None) -> Optional[Tuple[chess.Move, chess.engine.InfoDict]]:
    if options is None:
        options = {}

    if options.get("__action__") == "reset":
        if hasattr(opening_move, "tb") and getattr(opening_move, "tb") is not None:
            try:
                getattr(opening_move, "tb").close()
            except Exception:
                pass
            setattr(opening_move, "tb", None)
        setattr(opening_move, "csv_openings", [])
        setattr(opening_move, "csv_path", None)
        return None

    def ensure_tb() -> None:
        tb_paths = options.get("SyzygyPath")
        if tb_paths:
            raw_paths = tb_paths if isinstance(tb_paths, list) else [tb_paths]
            paths = [p for p in raw_paths if isinstance(p, str) and p]
        else:
            paths = []
        old_paths = getattr(opening_move, "tb_paths", None)
        if old_paths != paths:
            if hasattr(opening_move, "tb") and getattr(opening_move, "tb") is not None:
                try:
                    getattr(opening_move, "tb").close()
                except Exception:
                    pass
                setattr(opening_move, "tb", None)
            setattr(opening_move, "tb_paths", paths)
            if paths:
                try:
                    tb = chess.syzygy.open_tablebase(paths[0])
                    for p in paths[1:]:
                        tb.add_directory(p)
                    setattr(opening_move, "tb", tb)
                except Exception:
                    setattr(opening_move, "tb", None)

    def tb_in_range(b: chess.Board) -> bool:
        limit = options.get("TablebaseProbeLimit")
        if isinstance(limit, int) and 3 <= limit <= 7:
            probe_limit = limit
        else:
            probe_limit = 7
        return chess.popcount(b.occupied) <= probe_limit and b.uci_variant == "chess"

    def tb_best_move(b: chess.Board) -> Optional[chess.Move]:
        try:
            tb = getattr(opening_move, "tb", None)
            assert tb is not None
            best = None
            best_wdl = -999
            for m in b.legal_moves:
                b.push(m)
                try:
                    wdl = -tb.probe_wdl(b)
                except Exception:
                    wdl = -999
                b.pop()
                if wdl > best_wdl:
                    best_wdl = wdl
                    best = m
            return best
        except Exception:
            return None

    def ensure_csv_openings() -> None:
        path = options.get("CSVOpeningsPath") or "engines/openings.csv"
        current_path = getattr(opening_move, "csv_path", None)
        openings_cache = getattr(opening_move, "csv_openings", [])
        if openings_cache and current_path == path:
            return
        use_csv = options.get("UseCSVOpenings")
        if use_csv is False:
            setattr(opening_move, "csv_openings", [])
            setattr(opening_move, "csv_path", path)
            return
        openings: List[Tuple[str, str, List[chess.Move]]] = []
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
                        eco = (row.get("ECO Code") or row.get("ECO") or row.get("eco") or "").strip()
                        name = (row.get("Name") or row.get("name") or "").strip()
                        moves_str = (
                            row.get("Opening Moves")
                            or row.get("moves")
                            or row.get("Moves")
                            or ""
                        ).strip()
                        if not moves_str:
                            continue
                        b = chess.Board()
                        parsed_moves: List[chess.Move] = []
                        tokens = moves_str.replace(".", " ").split()
                        for tok in tokens:
                            if tok.isdigit():
                                continue
                            try:
                                mv = b.parse_san(tok)
                                parsed_moves.append(mv)
                                b.push(mv)
                            except Exception:
                                continue
                        if parsed_moves:
                            openings.append((eco, name or eco or "Opening", parsed_moves))
                break
            except Exception:
                continue
        setattr(opening_move, "csv_openings", openings)
        setattr(opening_move, "csv_path", path)

    def find_csv_opening_move(b: chess.Board) -> Optional[Tuple[chess.Move, str]]:
        if options.get("UseCSVOpenings") is False:
            return None
        ensure_csv_openings()
        current_moves = list(b.move_stack)
        ply = len(current_moves)
        candidates: List[Tuple[chess.Move, str]] = []
        for eco, name, moves in getattr(opening_move, "csv_openings", []):
            if ply >= len(moves):
                continue
            match = True
            for i, m in enumerate(current_moves):
                if i >= len(moves) or m != moves[i]:
                    match = False
                    break
            if not match:
                continue
            next_move = moves[ply]
            if next_move in b.legal_moves:
                candidates.append((next_move, name))
        if not candidates:
            return None
        return random.choice(candidates)

    def book_move(b: chess.Board) -> Optional[chess.Move]:
        use_book = options.get("UseBook")
        if use_book is False:
            return None
        book_paths = options.get("Book")
        paths = book_paths if isinstance(book_paths, list) else ([book_paths] if book_paths else [])
        min_weight = options.get("BookMinWeight", 1)
        randomize = options.get("RandomizeBook", True)
        for path in paths:
            try:
                with chess.polyglot.open_reader(path) as reader:
                    entries = list(reader.find_all(b))
                    entries = [e for e in entries if e.weight >= min_weight]
                    if not entries:
                        continue
                    if randomize:
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

    ensure_tb()
    if hasattr(opening_move, "tb") and getattr(opening_move, "tb") is not None and tb_in_range(board):
        m = tb_best_move(board)
        if m is not None:
            info: chess.engine.InfoDict = {"string": "lichess-bot-source:Syzygy EGTB", "pv": [m], "depth": 0, "nodes": 0}
            return m, info

    csv_pick = find_csv_opening_move(board)
    if csv_pick:
        m, opening_name = csv_pick
        info: chess.engine.InfoDict = {"string": f"lichess-bot-source:CSV Opening - {opening_name}", "pv": [m], "depth": 0, "nodes": 0}
        return m, info

    m = book_move(board)
    if m is not None:
        info: chess.engine.InfoDict = {"string": "lichess-bot-source:Polyglot Opening Book", "pv": [m], "depth": 0, "nodes": 0}
        return m, info

    return None
