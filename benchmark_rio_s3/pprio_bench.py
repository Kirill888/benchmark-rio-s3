from timeit import default_timer as t_now
from types import SimpleNamespace
import rasterio
import sys
from .pprio import ParallelReader


class PReadRIO_bench(object):
    def __init__(self, nthreads,
                 region_name=None,
                 use_ssl=True,
                 bytes_at_open=None,
                 aws_unsigned=False):
        self._nthreads = nthreads
        self._use_ssl = use_ssl  # At least for now we ignore this param
        self._proc = ParallelReader(nthreads,
                                    region_name=region_name,
                                    bytes_at_open=bytes_at_open,
                                    aws_unsigned=aws_unsigned)

    def warmup(self):
        return self._proc.warmup()

    def read_blocks(self,
                    urls,
                    block_idx,
                    dst,
                    band=1):
        t0 = t_now()
        stats = [None for _ in urls]

        def extract_block(f, idx, t0=0):
            dst_slice = dst[idx, :, :]
            win = f.block_window(band, *block_idx)
            t1 = t_now()
            f.read(band, window=win, out=dst_slice)
            t2 = t_now()
            try:
                chunk_size = f.block_size(band, *block_idx)
            except rasterio.errors.RasterBlockError:
                print('Failed to read block size for {}'.format(f.name), file=sys.stderr)
                chunk_size = 0  # probably GDAL specific 0 sized tile

            stats[idx] = SimpleNamespace(t_open=t1-t0,
                                         t_total=t2-t0,
                                         t0=t0,
                                         chunk_size=chunk_size)

        self._proc.process(enumerate(urls), extract_block, timer=t_now)

        t_total = t_now() - t0
        params = SimpleNamespace(nthreads=self._nthreads,
                                 band=band,
                                 block_shape=dst.shape[1:],
                                 dtype=dst.dtype.name,
                                 block=block_idx)

        return dst, SimpleNamespace(stats=stats,
                                    params=params,
                                    t0=t0,
                                    t_total=t_total)
