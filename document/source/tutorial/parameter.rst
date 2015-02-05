複数のパラメータで実験する
==========================

..
   対象読者：パラメータをつかわないタスクとコマンドルールの書き方がわかっている人
   目標：パラメータをつかった実験が書けるようになる

この章では、パラメータをつかって複数のタスクをいっぺんに定義する方法を学びます。
ここからしばらくは、 `LIBLINEAR をつかったサンプル <https://github.com/pfi/maf/blob/master/samples/liblinear/wscript>`_ を題材として扱います。

実験内容
--------

`LIBLINEAR <http://www.csie.ntu.edu.tw/~cjlin/liblinear/>`_ は、台湾大学で開発されているオープンソース・ソフトウェアで、線形予測器学習の高速な実装です。
LIBLINEAR をつかうと、文書分類などの課題を解くことができます。
まずは LIBLINEAR をインストールしましょう。
Linux または Mac OS X の多くの環境では、パッケージが用意されています。

.. code-block:: sh

   環境に合わせていずれかを実行
   $ apt-get install liblinear-tools
   $ yum install liblinear
   $ brew install liblinear

LIBLINEAR には 8 種類の分類学習アルゴリズムと、3 種類の回帰学習アルゴリズムが実装されています。
ここでは文書分類を目標として、前者の 8 種類のアルゴリズムを比較する実験を書いてみましょう。

そのために、文書分類のデータセットを準備します。
LIBLINEAR のウェブサイトには様々なデータセットが LIBLINEAR 用のフォーマットで用意されているので、これを利用しましょう。
ここでは、ニュース記事分類のデータセットである `20 Newsgroup Dataset <http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass.html#news20>`_ を使います。
このうち ``news20.scale.bz2`` と ``news20.t.scale.bz2`` をダウンロード、展開しておきましょう。

.. code-block:: sh

   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/news20.scale.bz2
   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/news20.t.scale.bz2
   $ bunzip2 news20.scale.bz2
   $ bunzip2 news20.t.scale.bz2

これで ``news20.scale`` と ``news20.t.scale`` という 2 つのファイルができます。
これらはそれぞれ、学習の際の訓練データと評価用データです。

今回の wscript は以下です。

.. code-block:: python

   import maf
   import maflib.util

   def configure(conf):
       pass

   def build(exp):
       exp(source='news20.scale',
           target='model',
           parameters=maflib.util.product({
               's': [0, 1, 2, 3, 4, 5, 6, 7],
               'C': [0.001, 0.01, 0.1, 1, 10, 100],
               'B': [1, -1]
           }),
           rule='liblinear-train -s ${s} -c ${C} -B ${B} ${SRC} ${TGT} > /dev/null')

       exp(source=['news20.t.scale', 'model'],
           target='result',
           rule='liblinear-predict ${SRC} /dev/null > ${TGT}')

パラメータを使わない実験
------------------------

まずはじめに、実験の内容を考えましょう。
LIBLINEAR には様々な手法が用意されており、またそれらに対して調節できるオプションもあります。
これらをいろいろ変えたときに、性能がどのように変わるかを評価するのが目標です。

LIBLINEAR は以下のコマンドでつかいます。

.. code-block:: sh

   $ liblinear-train -s [手法] -c [オプション1] -B [オプション2] [訓練データ] [モデル（出力）]
   $ liblinear-predict [モデル] [分類結果] > [メッセージ]

「モデル」というのは学習結果のことで、このファイルが学習された分類方法を表しています。
``liblinear-predict`` の標準出力には、正解率を含むメッセージが出されます。
手法は 0 から 7 までの 8 通りの値をとります。
オプション1 は正の数値が指定できます。
オプション2 はここでは 1 と -1 の 2 通りの値をつかうことにします。
これらをいろいろに変えて、正解率を比べるのが目標です。

まずは単純に、ある一つの手法・オプションについて実験を書いてみましょう。

.. code-block:: python

   exp(source='news20.scale',
       target='model',
       rule='liblinear-train -s 0 -c 1 -B 1 ${SRC} ${TGT}')

   exp(source='model',
       target='result',
       rule='liblinear-result ${SRC} /dev/null > ${TGT}')

今は分類結果（各評価用データに対してモデルが振ったラベル）は必要ないので、結果を捨てる意味で ``/dev/null`` を指定します。
一方、正解率が書いてあるメッセージがみたいので、それを ``result`` ノードに保存しています。

これで、ある ``-s`` ``-c`` ``-B`` の組み合わせに対する実験は書けました。
さて、これをいろんな組み合わせに拡張したいですが、どのようにしたらよいでしょうか？

まず ``-s`` を考えます。
wscript は Python スクリプトなので、たとえばループを回せばすべての手法を実験できます。

.. code-block:: python

   for s in range(8):
       model = 'model_s=%d' % s
       result = 'result_s=%d' % s

       exp(source='news20.scale',
           target=model,
           rule='liblinear-train -s %d -c 1 -B 1 ${SRC} ${TGT}' % s)

       exp(source=model,
           target=result,
           rule='liblinear-predict ${SRC} /dev/null > ${TGT}')

このように、各手法 ``s`` ごとに異なる名前のノードを作って、ルールも ``-s`` のところだけ違うものをつかえば、各手法を実験することができます。
このとき、ノードの名前は自分で管理する必要があります。

さて、これを実験してから、今度 ``-B`` オプションも動かしたくなったとします。
これは、次のようにループを増やして、ノード名のつけかたを変えればよいです。

.. code-block:: python

   for s in range(8):
       for B in (-1, 1):
           model = 'model_s=%d_B=%d' % (s, B)
           result = 'result_s=%d_B=%d' % (s, B)

           exp(source='news20.scale',
               target=model,
               rule='liblinear-train -s %d -c 1 -B %d ${SRC} ${TGT}' % (s, B))

           exp(source=model,
               target=result,
               rule='liblinear-predict ${SRC} /dev/null > ${TGT}')

もとの wscript からこのように変更したあとで再実験すると、すべての実験はやり直しです。
本当は、 ``B=1`` の場合の実験はやり直さなくてもよかったはずです。
また、名前付けはオプションが増えれば増えるほどややこしくなっていきます。

パラメータづけられたタスクとメタノード
--------------------------------------

**パラメータ** をつかうと、このようなオプションだけが違うタスクをいっぺんに書くことができます。
パラメータをつかうには、 ``exp`` の引数に ``parameters`` を指定します。

:parameters: パラメータのリスト。
             各パラメータとしてはハッシュ可能な値をもつ辞書を渡すことができます。
             パラメータの内容はルールのシェルスクリプト内で変数展開できます。

これが何者なのか知るには、具体例をみるのが早いでしょう。
まず ``model`` タスクをパラメータで書いてみます。

.. code-block:: python

   exp(source='news20.scale',
       target='model',
       parameters=[ {'s': s} for s in range(8) ],  # 1
       rule='liblinear-train -s ${s} -c 1 -B 1 ${SRC} ${TGT}'  # 2
       )

(1) ``parameters`` 引数に辞書のリストを渡します。
    ここでは ``s`` というキーに 0 から 7 までの整数値をとる辞書のリストを渡しています。
    これが実験する設定のバリエーションに対応します。
(2) ルールのシェルスクリプト内では、 ``SRC`` や ``TGT`` と同じようにパラメータを展開できます。

このように ``parameters`` が指定されたタスクは **パラメータづけられたタスク** と呼びます。

``build`` 関数を上の ``model`` タスクだけにして、一度実験してみましょう。
ただし、これには少し時間がかかります。
急ぐ方は ``range(8)`` の部分を適宜 ``range(2)`` など少なくして実験してみてください。

``./waf`` を実行すると、8 回 ``liblinear-train`` が実行されたと思います。
``build`` ディレクトリを見てみましょう。

::

   build
   ├── c4che
   │   ├── _cache.py
   │   └── build.config.py
   ├── config.log
   └── model
       ├── 0-model
       ├── 1-model
       ├── 2-model
       ├── 3-model
       ├── 4-model
       ├── 5-model
       ├── 6-model
       └── 7-model

さて、 ``model`` にはとくにパラメータごとに名前をつけませんでしたが、実験結果をみてみると ``model`` はディレクトリになっていて、その中に 8 個のファイルが生成されています。
実は、これらが 8 個のパラメータに対応する ``model`` になっています。
ディレクトリである ``model`` には 8 通りのパラメータが紐付けられており、1 つのパラメータを指定するとその中の 1 つのファイルが定まる仕組みです。

この ``model`` のように、パラメータが紐付けられたディレクトリのことを **メタノード** と呼びます。
メタノードは、厳密にはノードではありません。
メタノードはディレクトリであって、中に各パラメータに対応するノードを含んでいるもの、というのが厳密な理解です。

メタノードの中に入っている具体的なノードは、どのパラメータに対応しているのでしょうか？
この対応を知るには、 ``build/.maf_id_table.tsv`` というファイルを見る必要があります。

.. code-block:: sh

   $ cat build/.maf_id_table.tsv
   0	{'s': 0}
   1	{'s': 1}
   2	{'s': 2}
   3	{'s': 3}
   4	{'s': 4}
   5	{'s': 5}
   6	{'s': 6}
   7	{'s': 7}

このファイルは **IDテーブル** といいます。
IDテーブルには、番号とそれに対応するパラメータ（辞書）が書かれています。
番号は、メタノード内の各ノード名の先頭についている整数に対応しています。

TODO
