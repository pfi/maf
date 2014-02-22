最初の実験
----------

最初に maf を用いた簡単な実験を紹介します。
この節は予備知識がなくても読めるようになっています。

まずお好きな場所に空の実験ディレクトリを作りましょう。
そこに ``waf`` と ``maf.py`` を起きます。
``waf`` には実行権限を与えておくと便利です。

.. code-block:: sh

   $ wget https://github.com/pfi/maf/raw/master/waf
   $ wget https://github.com/pfi/maf/raw/master/maf.py
   $ chmod +x waf

実験手順は ``wscript`` というファイルに書いていきます。
まずは何もしない wscript を書いてみましょう。

TODO
