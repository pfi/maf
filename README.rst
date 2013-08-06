=====
 maf
=====

**maf** is a waf extension for writing computational experiments.
The main target of maf is experiments of machine learning, but it is useful for any type of computational experiments.

Usage
=====

Create a directory to run experiments.
Copy ``waf`` and ``maf.py`` into it.
Write a file named ``wscript`` that describes procedure of experiments into this directory.
Then run following commands:

::

  $ ./waf configure
  $ ./waf experiment

More detail
===========

More detailed description of usage is in ``document`` directory.
Currently only Japanese document is available.
