from src.constants import MOVES, BOARD_SIZE


def manhattan_distance(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def get_step_towards(curr_pos, target_pos):
    """Return direction move string to get 1 step closer to target_pos."""
    cx, cy = curr_pos
    tx, ty = target_pos
    if cx < tx:
        return "EAST"
    if cx > tx:
        return "WEST"
    if cy < ty:
        return "SOUTH"
    if cy > ty:
        return "NORTH"
    return None


def plan_manhattan_path(start_pos, target_pos):
    """Generate list of direction moves to walk from start_pos to target_pos."""
    moves = []
    curr = list(start_pos)
    while curr[0] != target_pos[0] or curr[1] != target_pos[1]:
        step = get_step_towards(curr, target_pos)
        if step is None:
            break
        moves.append(step)
        dx, dy = MOVES[step]
        curr[0] += dx
        curr[1] += dy
    return moves


def solve_tsp_nearest_neighbor(start_pos, targets):
    """Solve TSP using Nearest Neighbor heuristic + 2-opt refinement."""
    if not targets:
        return []
    
    remaining = list(targets)
    route = []
    curr = start_pos
    
    while remaining:
        # Find closest target
        best_idx = 0
        best_dist = manhattan_distance(curr, remaining[0][0])
        for idx in range(1, len(remaining)):
            dist = manhattan_distance(curr, remaining[idx][0])
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        
        chosen = remaining.pop(best_idx)
        route.append(chosen)
        curr = chosen[0]
        
    # 2-opt optimization
    improved = True
    iterations = 0
    max_iterations = 20
    
    def total_route_len(r):
        if not r:
            return 0
        dist = manhattan_distance(start_pos, r[0][0])
        for i in range(len(r) - 1):
            dist += manhattan_distance(r[i][0], r[i+1][0])
        return dist

    while improved and iterations < max_iterations:
        improved = False
        iterations += 1
        best_len = total_route_len(route)
        for i in range(len(route) - 1):
            for j in range(i + 1, len(route)):
                new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                new_len = total_route_len(new_route)
                if new_len < best_len:
                    route = new_route
                    best_len = new_len
                    improved = True
                    break
            if improved:
                break
                
    return route
