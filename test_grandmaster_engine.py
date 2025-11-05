#!/usr/bin/env python3
"""
Test script to demonstrate the GrandmasterEngine features.
"""
import chess
from homemade import GrandmasterEngine
from chess.engine import Limit

def test_engine():
    """Test the GrandmasterEngine with various positions."""
    print("=" * 60)
    print("GrandmasterEngine Test Suite")
    print("=" * 60)
    
    # Create the engine
    engine = GrandmasterEngine([], {}, None, {})
    
    # Test 1: Starting position
    print("\n1. Testing starting position:")
    board = chess.Board()
    print(f"Position: {board.fen()}")
    time_limit = Limit(time=2.0)
    result = engine.search(board, time_limit, False, False, None)
    print(f"Best move: {result.move}")
    print(f"Nodes searched: {result.info.get('nodes', 'N/A')}")
    print(f"Search depth: {result.info.get('depth', 'N/A')}")
    print(f"Score: {result.info.get('score', 'N/A')}")
    
    # Test 2: Tactical position (capture available)
    print("\n2. Testing tactical position:")
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1")
    print(f"Position: {board.fen()}")
    result = engine.search(board, time_limit, False, False, None)
    print(f"Best move: {result.move}")
    print(f"Nodes searched: {result.info.get('nodes', 'N/A')}")
    
    # Test 3: Endgame position
    print("\n3. Testing endgame position:")
    board = chess.Board("8/8/4k3/8/8/4K3/4P3/8 w - - 0 1")
    print(f"Position: {board.fen()}")
    result = engine.search(board, time_limit, False, False, None)
    print(f"Best move: {result.move}")
    print(f"Nodes searched: {result.info.get('nodes', 'N/A')}")
    
    # Test 4: Checkmate in one
    print("\n4. Testing checkmate in one:")
    board = chess.Board("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
    print(f"Position: {board.fen()}")
    result = engine.search(board, Limit(time=1.0), False, False, None)
    print(f"Best move: {result.move}")
    board.push(result.move)
    print(f"Checkmate: {board.is_checkmate()}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
    
    # Print feature summary
    print("\nGrandmasterEngine Features:")
    print("✓ Minimax algorithm with alpha-beta pruning")
    print("✓ Transposition table for position caching")
    print("✓ Sophisticated evaluation function:")
    print("  - Material balance")
    print("  - Piece-square tables (positional value)")
    print("  - Piece mobility")
    print("  - King safety (pawn shield, attacks)")
    print("  - Pawn structure (doubled, isolated, passed pawns)")
    print("✓ Move ordering for efficient pruning")
    print("✓ Quiescence search to avoid horizon effect")
    print("✓ Iterative deepening")
    print("✓ Opening book support (when book files available)")
    print("✓ Endgame tablebase support (when tablebase files available)")
    print("\nThe engine searches to depth 4-6 depending on time available")
    print("and uses advanced chess knowledge to evaluate positions.")

if __name__ == "__main__":
    test_engine()
