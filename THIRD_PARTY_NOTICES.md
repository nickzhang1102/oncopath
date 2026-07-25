# Third-Party Notices

OncoPath is licensed under the Apache License 2.0. Third-party packages and
assets keep their own licenses; the project license does not replace them.

## PDFium and pypdfium2

The backend uses `pypdfium2` to render and inspect PDF documents. pypdfium2 is
distributed under Apache-2.0 and BSD-3-Clause terms. Its bundled PDFium binary
is distributed under the BSD-3-Clause license and includes third-party
components listed by the upstream PDFium project.

- Project: https://github.com/pypdfium2-team/pypdfium2
- License files: https://github.com/pypdfium2-team/pypdfium2/tree/main/LICENSES

The project does not distribute or depend on PyMuPDF/AGPL.

## WenQuanYi Zen Hei

The backend Docker image installs the Debian `fonts-wqy-zenhei` package for CJK
PDF rendering. The font remains under its upstream GPL-2.0-or-later terms with
the font embedding exception supplied by the package.

- Project: http://wenq.org/wqy2/
- Debian copyright metadata: `/usr/share/doc/fonts-wqy-zenhei/copyright` in the
  built image

## Other Dependencies

Python and npm dependencies are installed from `back/requirements.txt` and
`front/package-lock.json`. Their package metadata and bundled license files are
the authoritative notices for those components. Redis, PostgreSQL, Nginx,
Chromium, PaddlePaddle, PaddleOCR and other container components also retain
their respective upstream licenses.
