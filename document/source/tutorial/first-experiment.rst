最初の実験
----------

最初に maf を用いた簡単な実験を紹介します。
この節は予備知識がなくても読めるようになっています。

空の実験
~~~~~~~~

まずお好きな場所に空の実験ディレクトリを作りましょう。
そこに ``waf`` と ``maf.py`` をダウンロードしてきます。
``waf`` には実行権限を与えておくと便利です。

.. code-block:: sh

   $ wget https://github.com/pfi/maf/raw/master/waf
   $ wget https://github.com/pfi/maf/raw/master/maf.py
   $ chmod +x waf

実験手順は ``wscript`` というファイルに書いていきます。
まずは何もしない wscript を書いてみましょう。

.. code-block:: python

   import maf  # 1

   def configure(conf): pass  # 2

   def experiment(exp): pass  # 3

1. ``import maf`` は maf を使うために必要な一文です。
   ここで ``maf.py`` が読み込まれ waf が拡張されます。
2. この関数はビルドツールにおける configure 相当の役割を持ちます。
   実験全体の設定を事前に行うために使います。
   空でも必ず定義しなくてはなりません（これは waf の仕様です）。
3. 実験手順は ``experiment`` 関数に書きます。

今は何もしない実験であるため、各関数は空になっています。
この状態で maf を動かしてみましょう。

.. code-block:: sh

   $ ./waf configure  # 1
   Setting top to                           : /path/to/pwd
   Setting out to                           : /path/to/pwd/build
   'configure' finished successfully (0.003s)
   
   $ ./waf experiment  # 2
   Waf: Entering directory '/path/to/pwd/build/experiment'
   Waf: Leaving directory '/path/to/pwd/build/experiment'
   'experiment' finished successfully (0.004s)

1. 実験の前に必ず ``configure`` コマンドを実行します。
   ``configure()`` 関数にオプションの設定などをすることで、このコマンドに引数を渡して設定を保存することができます。
2. 実験本体は ``experiment`` コマンドで実行します。

正しく実行されていれば上記のような出力が得られます（メッセージ中の ``/path/to/pwd`` には作業ディレクトリへのパスが入ります）。
まだ何も実験手順を書いていないので、何も実行されません。

簡単な実験
~~~~~~~~~~

TODO
