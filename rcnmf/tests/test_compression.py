"""
   Copyright (c) 2015, Mariano Tepper, Duke University.
   All rights reserved.

   This file is part of RCNMF and is under the BSD 3-Clause License,
   which can be found in the LICENSE file in the root directory, or at
   http://opensource.org/licenses/BSD-3-Clause
"""

from __future__ import absolute_import
import numpy as np
from dask.array import Array, random
from dask.array.into import discover
import blaze
import time
import h5py
import os
import matplotlib.pyplot as plt
import rcnmf.compression as randcomp
import tempfile


def size_timing(m, n, q):

    def select_blocksize(k):
        blocksize = 1
        while k / (10 * blocksize) >= 1:
            blocksize *= 10
        return min(blocksize, int(1e4))

    blockshape = (select_blocksize(m), select_blocksize(n))
    print(blockshape)

    X_disk = random.standard_normal(size=(m, n),
                                    blockshape=blockshape)
    X_disk = blaze.Data(X_disk)

    temp_file = tempfile.NamedTemporaryFile(suffix='.hdf5')
    filename = temp_file.name

    blaze.into(filename + '::/X', X_disk)

    hdf5size = os.path.getsize(filename)

    t = time.clock()
    randcomp.compress(filename + '::/X', q,
                      blockshape=blockshape)
    tid = time.clock() - t

    print float(hdf5size) / (6 * (2**30))

    if hdf5size < 6 * (2**30):
        data_array = blaze.into(Array, filename + '::/X',
                                blockshape=blockshape)
        X = blaze.into(np.ndarray, blaze.Data(data_array))
        t = time.clock()
        randcomp.compress(X, q, n_power_iter=0)
        tim = time.clock() - t
    else:
        tim = np.nan

    temp_file.close()

    return hdf5size, tid, tim


def run():
    only_draw = False

    # sizes_m = map(int, [5e3, 1e4, 5e4, 1e5, 2e5, 5e5, 1e6])
    sizes_m = map(int, [5e3, 1e4])
    n = int(5e3)
    q = 10
    repetitions = 1

    if not only_draw:
        shape = (len(sizes_m), repetitions)
        times_in_disk = np.zeros(shape)
        times_in_memory = np.zeros(shape)
        hdf5sizes = np.zeros((len(sizes_m), 1))

        for i, s in enumerate(sizes_m):
            print i, s
            for k in range(repetitions):
                res = size_timing(s, n, q)
                hdf5sizes[i] = res[0]
                times_in_disk[i, k] = res[1]
                times_in_memory[i, k] = res[2]

        times_in_disk = np.mean(times_in_disk, axis=1)
        times_in_memory = np.mean(times_in_memory, axis=1)
        hdf5sizes /= 2**30

        with open('test_compression_result', 'w') as f:
            np.save(f, times_in_disk)
            np.save(f, times_in_memory)
            np.save(f, hdf5sizes)

    with open('test_compression_result', 'r') as f:
        times_in_disk = np.load(f)
        times_in_memory = np.load(f)
        hdf5sizes = np.load(f)

    print sizes_m
    print hdf5sizes
    print times_in_memory
    print times_in_disk
    print map(lambda a, b: a/b, times_in_disk, times_in_memory)

    fig = plt.figure()
    ax1 = plt.axes()

    ax1.hold(True)
    line1 = ax1.loglog(sizes_m, times_in_memory,
                       label='In-core',
                       linewidth=2, linestyle='-', color='b')
    line3 = ax1.loglog(sizes_m, times_in_disk,
                       label='Out-of-core',
                       linewidth=2, linestyle='-', color='r')
    ax1.hold(False)
    ax1.set_xlim(4e3, max(sizes_m) + 4e3)

    ax1.set_xticks(sizes_m)
    ax1.set_xticklabels(sizes_m)
    ax1.set_xlabel(r'Number $m$ of rows')
    ax1.set_ylabel('Time (s)')

    ax1.legend(loc='upper left')

    ax2 = ax1.twiny()
    ax2.loglog(sizes_m, times_in_memory, linewidth=0)

    ax2.set_xlim(4e3, max(sizes_m) + 4e3)

    ax2.set_xticks(sizes_m)
    ax2.set_xticklabels(["%.1f" % z for z in hdf5sizes])
    ax2.set_xlabel('Size of the hdf5 file (GB)')


if __name__ == '__main__':
    run()
    plt.show()