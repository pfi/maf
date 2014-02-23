最初の実験
----------

最初に maf を用いた簡単な実験を紹介します。
この節は Python の基本的な知識があれば読めるようになっています。

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
   引数 ``exp`` は **実験コンテキスト** と呼ばれ、 :py:class:`maflib.core.ExperimentContext` クラスのインスタンスが渡されます。
   この実験コンテキストを通じて実験手順を構築します。

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

最初の実験として、 `LIBLINEAR <http://www.csie.ntu.edu.tw/~cjlin/liblinear/>`_ を用いた分類タスクの簡単な実験を書いてみます。
以下のコマンドであらかじめ LIBLINEAR をインストールしておきましょう。

.. code-block:: sh

   $ sudo apt-get install liblinear1 liblinear-tools  # apt
   $ sudo yum install liblinear liblinear-devel  # yum
   $ brew install liblinear  # homebrew

今回は `MNIST <http://yann.lecun.com/exdb/mnist/>`_ というデータセットを使うことにします。
これはグレースケールの手書き数字 7 万枚からなるデータセットです。
LIBSVM のサイトに `前処理が施されたもの <http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass.html#mnist>`_ が置いてあります。
``mnist.scale`` と ``mnist.scale.t`` をあらかじめダウンロード・展開しておき、 ``wscript`` と同じディレクトリに置きます。

.. code-block:: sh

   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/mnist.scale.bz2
   $ wget http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/mnist.scale.t.bz2
   $ bunzip2 *.bz2
   $ ls
   maf.py  mnist.scale  mnist.scale.t  waf   wscript

今回は LIBLINEAR を使って訓練データ ``mnist.scale`` を学習し、得られた分類器をテストデータ ``mnist.scale.t`` に適用して正解率を出すところまでを行います。
これらは次の二行のコマンドで実行できます。

.. code-block:: sh

   $ liblinear-train -s 3 -B 1 mnist.scale model > /dev/null  # 1
   $ liblinear-predict mnist.scale.t model result > accuracy  # 2

1. ``mnist.scale`` を入力として学習結果のモデルファイル ``model`` を作成します。
   引数 ``-s 3 -B 1`` は学習器の設定ですが、今は決め打ちということにしておきます。
2. 学習済みのモデル ``model`` を ``mnist.scale.t`` に適用して、分類結果を ``result`` に、正解率を含むメッセージを ``accuracy`` に書き出します。
   ``result`` には N 個目のサンプルに対する分類結果が N 行目に入るようなファイルができます。

まず一行目から maf 上に書いてみましょう。

.. code-block:: python

   import maf

   def configure(conf): pass

   def experiment(exp):
       exp(source='mnist.scale',
           target='model',
           rule='liblinear-train -s 3 -B 1 ${SRC} ${TGT} > /dev/null')

実験コンテキスト ``exp`` を関数のように呼び出すことで **タスク** を作れます。
タスクは実験手順の 1 ステップです。
ここではタスク追加に 3 つの引数を設定しています。

``source``
  入力ノード（今はファイルと思ってもらって構いません）を指定します。
  ここでは訓練データ ``mnist.scale`` を設定しています。
``target``
  出力ノードを指定します。
  好きな名前をつけられますが、ここでは ``'model'`` という名前をつけています。
``rule``
  ここに処理内容（ **ルール** ）を書きます。
  文字列を渡すと、その内容をコマンドとして実行します。
  文字列内で ``${SRC}`` と書くとそこに入力ノードへのパスを代入します。
  ``${TGT}`` と書くと出力ノードへのパスを代入します。
  ルールにはコマンド以外にも Python の関数を渡すこともできます。

上の段階で実験を走らせてみましょう。

.. code-block:: sh

   $ ./waf experiment
   Waf: Entering directory '/path/to/pwd/build/experiment'
   [1/1] model: mnist.scale -> build/experiment/model
   Waf: Leaving directory '/path/to/pwd/build/experiment'
   'experiment' finished successfully (44.221s)

学習にしばらく時間がかかりますが、無事に終了します。
さて、学習結果のモデルファイル ``model`` はどこに出力されるのでしょうか？
maf ではすべての出力は ``build/experiment`` ディレクトリに置かれます。
よってモデルファイルは ``build/experiment/model`` に出力されます。

次にこのモデルをテストデータ ``mnist.scale.t`` に適用して評価するタスクを追加しましょう。

.. code-block:: python

   import maf

   def configure(conf): pass

   def experiment(exp):
       exp(source='mnist.scale',
           target='model',
           rule='liblinear-train -s 3 -B 1 ${SRC} ${TGT} > /dev/null')

       exp(source=['mnist.scale.t', 'model'],  # 1
           target=['result', 'accuracy'],  # 2
           rule='liblinear-predict ${SRC} ${TGT[0].abspath()} > ${TGT[1].abspath()}')  # 3

1. 今度はテストデータとモデルファイルという二つの入力ノードを指定しています。
   ``source`` や ``target`` に複数ノードを指定する場合、配列で渡すか、あるいはスペース区切りの文字列で渡します。
2. 出力ノードも分類結果 ``result`` と正解率 ``accuracy`` という二つを指定しています。
3. 入力や出力が複数ノードある場合、単に ``${SRC}`` や ``${TGT}`` と書くとそれらのパスをスペース区切りで順に埋め込まれます。
   一つずつ使いたい場合にはこの例のように ``${TGT[N].abspath()}`` のように書きます（ ``N`` にインデックスを入れます）。

さて、では実行してみましょう。

.. code-block:: sh

   $ ./waf experiment
   Waf: Entering directory '/path/to/pwd/build/experiment'
   [2/2] result,accuracy: mnist.scale.t build/experiment/model -> build/experiment/result build/experiment/accuracy
   Waf: Leaving directory '/path/to/pwd/build/experiment'
   'experiment' finished successfully (0.534s)

今度はすぐに完了しました。
``waf`` の機能により、変更が加えられた部分だけが再実行されます。
``wscript`` 上で生成方法や入力ノードの内容が変更されていない ``model`` については生成し直す必要が無いため、一つ目のタスクは実行されません。
正解率のファイルを見てみましょう。
出力ノードはすべて ``build/experiment`` 以下に生成されるのでしたから、正解率は ``build/experiment/accuracy`` に出力されます。

.. code-block:: sh

   $ cat build/experiment/accuracy
   Accuracy = 92.18% (9218/10000)

以上で最初の実験は終わりです。
まだ実験手順が簡単すぎるため maf で書くオーバーヘッドが大きいですが、これからより複雑な例を見ていけば、maf で書く利点が明らかになっていくでしょう。
