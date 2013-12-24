=====
 maf
=====

**maf** is a waf extension for writing computational experiments.
The main target of maf is experiments of machine learning, but it is useful for any type of computational experiments.

Usage
=====

Copy ``waf`` and ``maf.py`` into your favorite directory where you will write your own experiments, and (optionally) make ``waf`` executable.

::

  $ cd <directory-to-write-experiments>
  $ wget https://github.com/pfi/maf/raw/master/waf
  $ wget https://github.com/pfi/maf/raw/master/maf.py
  $ chmod +x waf

Write a procedure of experiments and save it as a text file named ``wscript`` into this directory.
Then run following commands:

::

  $ ./waf configure
  $ ./waf experiment

You can also build ``maf.py`` from the source code.
Clone this repository and execute following command. It generates ``maf.py``.

::

  $ python generate_maf.py

Documentation
=============

Document is available: http://pfi.github.io/maf/ (usage in Japanese and reference in English)

Document source code is in ``document`` directory.

Acknowledgments
===============

This project is supported by `New Energy and Industrial Technology Development Organization (NEDO) <http://www.nedo.go.jp/english/>`_.
