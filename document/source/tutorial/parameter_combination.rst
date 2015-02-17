パラメータを組み合わせる
========================

..
   対象読者：パラメータ付けられたタスクとメタノードについてなんとなく理解している人
   目標：複数のメタノードを入力とするタスクや、メタノードを入力とするパラメータづけられたタスクを読み書きできるようになる

前章で、パラメータづけられたタスクの書き方を学びました。
そこでは、メタノードと呼ばれるパラメータづけられたノードが導入されました。
本章では、メタノードやパラメータを複数組み合わせてつかった場合の挙動を学びます。

実験内容
--------

前章であつかった実験では、 `20 Newsgroup Dataset <http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass.html#news20>`_ を LIBLINEAR に学習させました。

アルゴリズムの評価をする際には、ひとつのデータセットを用いるだけだとその汎用性がわかりません。
そこで、複数のデータセットに対して同じ実験をよく行います。
LIBLINEAR のウェブサイトでは、ほかの文書分類のデータセットとして `RCV1 <http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass.html#rcv1.multiclass>`_ というものも公開されています。
本章では、前章の実験を少しだけ変更して、20 Newsgroup Dataset と RCV1 の両方で実験できるようにします。

まずは前章と同様に、データセットをダウンロード、展開しておきましょう。

.. code-block:: sh

   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/rcv1_train.multiclass.bz2
   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/rcv1_test.multiclass.bz2
   $ bunzip2 rcv1_train.multiclass.bz2
   $ bunzip2 rcv1_test.multiclass.bz2

これで ``rcv1_train.multiclass`` と ``rcv1_test.multiclass`` という 2 つのファイルができます。
それぞれ、訓練データと評価用データを表します。

また、今のところ maf では入力ファイルの名前の違いを吸収する仕組みはないので、wscript 内で処理する必要があります。
その処理で楽をするために、2 つのデータセットで命名規則を統一しておきましょう。
命名規則はなんでもよいですが、ここでは ``<データセット名>.<train|test>`` という名前にします。

.. code-block:: sh

   $ mv news20.scale          news20.train
   $ mv news20.t.scale        news20.test
   $ mv rcv1_train.multiclass rcv1.train
   $ mv rcv1_test.multiclass  rcv1.test

今回の wscript は以下です。
本当は LIBLINEAR への引数の組み合わせをより多く試した方がよいですが、チュートリアルとしては実行に時間がかかりすぎるので、前章よりもパラメータを減らしています。

.. code-block:: python

   import maf
   import maflib.util
   
   def configure(conf):
       pass

   def build(exp):
       for dataset in ('news20', 'rcv1'):
           exp(source='{}.train'.format(dataset),
               target='train_data',
               parameters=[{'dataset': dataset}],
               rule='cp ${SRC} ${TGT}')

           exp(source='{}.test'.format(dataset),
               target='test_data',
               parameters=[{'dataset': dataset}],
               rule='cp ${SRC} ${TGT}')

       exp(source='train_data',
           target='model',
           parameters=maflib.util.product({
               's': [0, 1, 2, 3, 4]
           }),
           rule='liblinear-train -s ${s} -c 1 -B 1 ${SRC} ${TGT} > /dev/null'
       )

       exp(source=['test_data', 'model'],
           target='result',
           rule='liblinear-predict ${SRC} /dev/null > ${TGT}')

今回のスクリプトの方針は「まずデータセットの違いをメタノードに埋め込んで、実験本体はそのメタノードに対しておこなう」というものです。
上のスクリプトでは、新しく加わった最初の ``for`` 文で ``train_data`` と ``test_data`` というメタノードをつくり、残りの実験はこれらをつかっています。

同じメタノードに複数回出力する
------------------------------

まずはじめに、データセットを ``train_data`` と ``test_data`` という 2 つのメタノードにまとめます。

.. code-block:: python

   for dataset in ('news20', 'rcv1'):
       exp(source='{}.train'.format(dataset),
           target='train_data',
           parameters=[{'dataset': dataset}],
           rule='cp ${SRC} ${TGT}')

       exp(source='{}.test'.format(dataset),
           target='test_data',
           parameters=[{'dataset': dataset}],
           rule='cp ${SRC} ${TGT}')

``for`` 文のなかでこれらのターゲットを出力しています。
このコードは、次のようにループを展開したものと同じ意味です。

.. code-block:: python

   exp(source='news20.train',
       target='train_data',
       parameters=[{'dataset': 'news20'}],  # 1
       rule='cp ${SRC} ${TGT}')

   exp(source='news20.test',
       target='test_data',
       parameters=[{'dataset': 'news20'}],  # 1
       rule='cp ${SRC} ${TGT}')

   exp(source='rcv1.train',
       target='train_data',                 # 2
       parameters=[{'dataset': 'rcv1'}],
       rule='cp ${SRC} ${TGT}')

   exp(source='rcv1.test',
       target='test_data',                  # 2
       parameters=[{'dataset': 'rcv1'}],
       rule='cp ${SRC} ${TGT}')

(1) はじめの 20 Newsgroup データセットに対する ``train_data`` タスクおよび ``test_data`` タスクは、ただファイルをコピーするだけの単純なものです。
    この例のように、パラメータを 1 つだけ指定してメタノードをつくることができます。
    これは一見して意味がないように見えますが、次の RCV1 データセットに対する処理を含めると、パラメータを指定する意味が出てきます。

(2) RCV1 データセットに対しても、同様にタスクをつくります。
    ここで重要なのは **同じターゲットに違うパラメータで重ねて出力している** ことです。
    前章では、ひとつのタスクに複数のパラメータを指定することで、複数のノードを含むメタノードをつくりました。
    この方法だと、パラメータごとに異なる入力ノードやルールを使うことができません。
    そのようなことをしたい場合には、上のように別々のタスクとして書きます。

maf の精神としては、あくまで同じメタノードには同じ処理を適用するのが一般的なやり方です。
同じターゲットへのタスクを 2 つ以上書くのは、ほかに手段がないときに限りましょう。
（この例のように、入力ファイルをパラメータで区別したい場合に必要となることが多いです）

パラメータづけられたタスクにメタノードを入力する
------------------------------------------------

スクリプトの残り部分は、ノード名を除いて前回のものと同じです。
まず、 ``model`` タスクをみます。

.. code-block:: python

   exp(source='train_data',
       target='model',
       parameters=maflib.util.product({
           's': [0, 1, 2, 3, 4]
       }),
       rule='liblinear-train -s ${s} -c 1 -B 1 ${SRC} ${TGT} > /dev/null'
   )

さて、 ``model`` タスクにはメタノード ``train_data`` を入力しています。
その上で、さらにタスク自身にパラメータを指定しています。
このように、入力ノードとタスクの両方がパラメータ付けられている場合、 maf は **入力ノードとタスクのパラメータの組み合わせのうち、食い違わないものすべてを試します。**

今回の例では、入力のメタノード ``train_data`` には ``dataset`` パラメータをつけていて、タスク自体には ``s, C, B`` という 3 つのパラメータをつけています。
これらは別々のパラメータなので、maf はすべての組み合わせで実験をおこないます。
ここでは ``dataset`` が 2 通り、 ``s, C, B`` が 8 * 6 * 2 = 96 通りですので、全部で 2 * 96 = 192 通りの実験をおこないます。

このタスクが出力する ``model`` メタノードには、 ``dataset, s, C, B`` の 4 つすべてがパラメータとして付与されます。

さて、「食い違わない」とはどういうことでしょうか？
上の ``model`` タスクを次のように変えたとします。

.. code-block:: python

   exp(source='train_data',
       target='model',
       parameters=maflib.util.product({
           'dataset': ['rcv1'],  # !!!
           's': [0, 1, 2, 3, 4]
       }),
       rule='liblinear-train -s ${s} -c 1 -B 1 ${SRC} ${TGT} > /dev/null'
   )

タスクのパラメータ指定に ``dataset`` パラメータを加えました。
この場合、入力メタノード ``train_data`` のパラメータとタスクのパラメータの間で ``dataset`` というキーが被っています。
このとき、maf は **被ったキーについては値が一致する組み合わせしか試しません。**
これが「食い違わないすべての組み合わせを試す」ということの詳しい意味です。

複数のメタノードを入力する
--------------------------

最後に ``result`` タスクをみてみましょう。

.. code-block:: python

   exp(source=['test_data', 'model'],
       target='result',
       rule='liblinear-predict ${SRC} /dev/null > ${TGT}')

このタスクには、 ``test_data`` と ``model`` という 2 つのファイルを入力しています。
これらは、ともにメタノードです。
このように、入力として複数のメタノードを指定した場合、maf は **各入力ノードのパラメータの組み合わせのうち、食い違わないものすべてを試します。**
ここでの「食い違わない」は、上で説明したものと同じ意味です。

今回の例では、 ``test_data`` と ``model`` では ``dataset`` パラメータが被っています。
ですので、 ``result`` タスクはこれらの入力で ``dataset`` パラメータが一致する組み合わせについてだけ実行されます。
つまり、20 Newsgroup データセットから得た ``model`` は、20 Newsgroup の ``test_data`` でしか評価しませんし、RCV1 データセットから得た ``model`` は、RCV1 の ``test_data`` でしか評価しません。

このタスクで得られる ``result`` メタノードには、入力ノードすべてにつけられたパラメータが含まれます。
今回の例では、 ``model`` につけられたパラメータが ``test_data`` につけられたパラメータを含んでいるので、 ``result`` メタノードは ``model`` メタノードと同じパラメータを持っています。

さて、今回の例ではあつかいませんでしたが、複数の入力メタノードとタスクへのパラメータづけを組み合わせることもできます。
この場合 maf は、ご想像のとおり、各入力メタノードとタスクのパラメータの組み合わせのうち、は食い違わないものすべてを試します。

まとめ
------

本章では maf の機能のうち、以下の項目を紹介しました。

- 同じメタノードに異なるパラメータのタスクで出力する
- パラメータづけられたタスクにメタノードを入力する
- 複数のメタノードを入力する

メタノードとパラメータづけを組み合わせてつかえるようになると、実験の幅がぐんと広がります。
次章では、パラメータ解説の最後として、異なるパラメータでの実験結果を集約する方法を学びます。
