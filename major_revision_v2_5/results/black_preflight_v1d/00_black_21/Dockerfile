FROM python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f
ENV CFLAGS='-O0 -g0' CXXFLAGS='-O0 -g0'
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential libfreetype6-dev libpng-dev pkg-config && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pip==23.0.1 setuptools==59.6.0 wheel==0.38.4 && pip install --no-cache-dir pytest==5.4.3 click==7.1.1 attrs==19.3.0 appdirs==1.4.3 toml==0.10.0 pathspec==0.7.0 regex==2020.4.4 typed-ast==1.4.1 mypy-extensions==0.4.3 typing-extensions==3.7.4.1 setuptools-scm==4.1.2 aiohttp==3.8.6 aiohttp-cors==0.7.0
RUN git clone --filter=blob:none --no-checkout https://github.com/psf/black /source && git -C /source worktree add --detach /buggy c071af761e1550c6e4ebab8e5af747d2d8fdd48e && git -C /source worktree add --detach /fixed 8e7848c63efe36f09e4651bece8c0efc34a1c3e1
RUN git -C /source show 8e7848c63efe36f09e4651bece8c0efc34a1c3e1:tests/test_black.py > /buggy/tests/test_black.py
RUN cd /buggy && python setup.py egg_info
RUN cd /fixed && python setup.py egg_info
ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
USER 65534:65534
WORKDIR /tmp
