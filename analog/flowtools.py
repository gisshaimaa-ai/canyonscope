import heapq

import numpy as np
from scipy.ndimage import maximum_filter, minimum_filter, uniform_filter

OFFSETS = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def fill_depressions(dem, eps=1e-3, sinks=None):
    """Priority-flood (Barnes et al., 2014): water can always flow to the map edge,
    or into `sinks` (cells treated as base level, e.g. a main-canyon floor)."""
    height, width = dem.shape
    filled = dem.astype('float64').copy()
    done = np.zeros(dem.shape, dtype=bool)
    heap = []
    if sinks is not None:
        for r, c in zip(*np.nonzero(sinks)):
            done[r, c] = True
            heap.append((filled[r, c], r, c))
    for r in range(height):
        for c in (0, width - 1):
            if not done[r, c]:
                done[r, c] = True
                heap.append((filled[r, c], r, c))
    for c in range(width):
        for r in (0, height - 1):
            if not done[r, c]:
                done[r, c] = True
                heap.append((filled[r, c], r, c))
    heapq.heapify(heap)
    while heap:
        z, r, c = heapq.heappop(heap)
        for dr, dc in OFFSETS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and not done[nr, nc]:
                done[nr, nc] = True
                filled[nr, nc] = max(filled[nr, nc], z + eps)
                heapq.heappush(heap, (filled[nr, nc], nr, nc))
    return filled


def flow_receivers(filled):
    """D8 steepest descent. Returns the flat index of the downstream cell (-1 = flows off the map)."""
    height, width = filled.shape
    padded = np.pad(filled, 1, constant_values=-np.inf)
    best = np.zeros(filled.shape)
    receiver = np.full(filled.shape, -1, dtype=np.int64)
    rows, cols = np.indices(filled.shape)
    for dr, dc in OFFSETS:
        neighbour = padded[1 + dr:1 + dr + height, 1 + dc:1 + dc + width]
        drop = (filled - neighbour) / np.hypot(dr, dc)
        inside = (rows + dr >= 0) & (rows + dr < height) & (cols + dc >= 0) & (cols + dc < width)
        better = (drop > best) & inside
        best[better] = drop[better]
        receiver[better] = ((rows + dr) * width + (cols + dc))[better]
    edge = np.zeros(filled.shape, dtype=bool)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    receiver[edge & (best <= 0)] = -1
    return receiver.ravel()


def accumulation(filled, receiver):
    order = np.argsort(filled.ravel())[::-1]  # high to low: upstream before downstream
    acc = np.ones(filled.size, dtype=np.int64)
    for cell in order:
        down = receiver[cell]
        if down >= 0:
            acc[down] += acc[cell]
    return acc


def main_stem(acc, receiver, inside_trunk):
    """Follow the largest flow upstream from the biggest outlet while inside the main canyon."""
    upstream = {}
    for cell, down in enumerate(receiver):
        if down >= 0:
            upstream.setdefault(down, []).append(cell)
    flat_trunk = inside_trunk.ravel()
    candidates = np.flatnonzero(flat_trunk)
    cell = candidates[np.argmax(acc[candidates])]
    stem = [cell]
    while True:
        options = [u for u in upstream.get(cell, []) if flat_trunk[u]]
        if not options:
            break
        cell = max(options, key=lambda u: acc[u])
        stem.append(cell)
    mask = np.zeros(acc.size, dtype=bool)
    mask[stem] = True
    return mask.reshape(inside_trunk.shape)


def entry_points(filled, receiver, floor):
    """For every cell, the first cell of its flow path that sits next to the main-canyon floor."""
    flat_floor = floor.ravel()
    entry = np.full(filled.size, -1, dtype=np.int64)
    for cell in np.argsort(filled.ravel()):  # low to high: downstream before upstream
        if flat_floor[cell]:
            continue
        down = receiver[cell]
        if down < 0:
            continue
        entry[cell] = cell if flat_floor[down] else entry[down]
    return entry.reshape(filled.shape)
