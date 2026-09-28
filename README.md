# reference-guided-rig-parts

一枚絵から2Dリギング用の編集可能なPSD・RGBAパーツを作成し、既存の分割パーツを補修するCodexスキルです。元画像の切り出しを出発点に、画像生成で隠れ面や接合を補い、再合成して元絵との一致を確認します。

## 作業の流れ

1. **初期パーツを切り出す** — 元画像の見えている画素を部品ごとのマスクで抽出し、透過パーツ・元座標・部品一覧・初期合成を保存します。元アルファと所有マスクを掛け合わせ、透明領域の残留RGBを可視化しません。
2. **元絵とパーツを並べる** — 左に名前付きの部品、右に正しく背景合成した元絵を置きます。部品同士は重ねず、既定は原寸1:1とし、案件の倍率・リサンプリング制約を守ります。
3. **再作成・補修する** — 両方を画像生成で同時参照し、隠れ面・根元・接合を補い、別部品の混入や不自然な断片化を修正します。
4. **元位置へ戻して検証する** — 許可された変換だけで位置・形状を合わせ、全身と局所を再合成比較します。遮蔽物を外した連続性、アルファ、PSDの編集性も確認します。

既存PSD／RGBAパーツがある場合は、それを編集開始点とし、不足部品だけ切り出します。切り出しだけで得られない面は推定補完として扱い、元絵から抽出した画素と区別します。

縮尺の固定と隠れ面の延長は別です。可視の座標を守りながら同じ座標系で面を補います。顔と首・二重線等の所有、PSD全体の順序方向と個別ペアの前後、クリッピング先を別々に検証します。順序・属性だけの訂正では画素を再生成せず、巻き戻しだけで元の修正依頼を完了としません。

## 扱う内容

- 一枚絵のパーツ分割、既存パーツの欠損・混入・形状の補修
- 目の一体再現から内部分割、元絵と一体版の両方への再合成比較
- 肩・腕・袖・衣装・髪の連続面、接合、非対称性、前後関係
- 未切断の影レイヤーを保持するPSD内クリッピング
- 部品台帳、比較画像、検証範囲を添えたPSD・RGBAパーツの引き渡し

深度生成、メッシュ・骨・表情・物理演算などのリグ設定は別工程です。単なる背景除去やアップスケールだけを目的とするスキルではありません。

## 導入

このリポジトリを、Codexの個人スキルディレクトリに `reference-guided-rig-parts` として配置します。標準の配置先は `~/.codex/skills/reference-guided-rig-parts`、`CODEX_HOME` を設定している場合はその下の `skills/reference-guided-rig-parts` です。

新規導入の例：

```sh
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
git clone https://github.com/seagetch/reference-guided-rig-parts.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/reference-guided-rig-parts"
```

既存の同名スキルがある場合は、ローカルの変更を確認してから更新してください。参照画像を含む `references/` と `scripts/` も配置します。

再作成・補修には画像生成／編集機能、比較には画像閲覧機能が必要です。画像生成が利用できない場合は、切り出し・参照シートの準備までを行い、再作成は未実施として扱います。スクリプトはPython 3.9以上で動作します。資料検査の `casebook.py` は外部ライブラリ不要、任意のアルファ処理補助 `reference_rgba.py` とその回帰テストにはPillowが必要です。

## 使い方

元絵、既存パーツがあればそのPSD／RGBA、修正したい範囲、出力先を指定します。

一枚絵から作る場合：

```text
$reference-guided-rig-parts を使い、この元画像から初期パーツを切り出し、
元絵と同時参照して再作成・補修してください。
元位置での再合成と隠れ面を検証し、編集可能なPSDと透過PNGを出力してください。
```

既存パーツを直す場合：

```text
$reference-guided-rig-parts を使い、元絵とこの分割PSDを参照して、
肩の接合と耳前後の髪を補修してください。既存の良い部分を保ち、
修正前後の再合成比較と残る課題を添えてください。
```

## 手順と画像事例

| 資料 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | 開始条件、共通工程、部位別資料への入口 |
| [制約・入力・版の管理](references/task-contract.md) | 画素尺度、元画像と候補の区別、採否、検査と版の対応 |
| [初期切り出しとアトラス](references/atlas-and-fitting.md) | 初期パーツの保存、同時参照、再作成、合わせ込み |
| [顔と目](references/face-and-eyes.md) | 一体の目から内部分割へ進む手順 |
| [身体・衣装・髪](references/body-clothing-hair.md) | 接合、連続面、非対称性、前後関係 |
| [影とPSD](references/shadows-and-psd.md) | 影の保持、クリッピング、保存後の検査 |
| [合否と引き渡し](references/acceptance.md) | 忠実度・構造・アルファ・編集性・読込の検証 |
| [casebook](references/casebook.md) | Aoの制作過程を使った7つの事例 |

casebookには画像16枚、指摘を中立的な作業指示・確認基準へ整理した9件の要約、当時の生成指示と検証記録を同梱しています。改善途中や棄却された案も含み、それぞれの採否と検証範囲を説明しています。

画像事例は工程を理解するための資料です。別のキャラクターへ適用するときは、その案件の元絵と編集対象を基準にします。元の作業フォルダやセッション全文ログは必要ありません。

## 資料の検査

リポジトリのルートで実行します。

```sh
python3 scripts/casebook.py --list        # 事例一覧
python3 scripts/casebook.py --case eyes  # 目の事例の資料パス
python3 scripts/casebook.py --verify     # 全資料のSHA-256・サイズ・PNG寸法
python3 -m unittest discover -s tests   # 参照アルファ処理の回帰テスト（Pillowが必要）
```

この検査はファイルの整合性を確認します。絵の品質、可動域、対象アプリでの読込は、それぞれ別に検証します。

参照画像の補助処理例：

```sh
python3 scripts/reference_rgba.py inspect source.png
python3 scripts/reference_rgba.py compose source.png reference-white.png --background '#ffffff'
python3 scripts/reference_rgba.py cutout source.png ownership-mask.png initial-part.png
```

既存ファイルは上書きしません。`cutout` のマスクは元画像と同寸法のLまたは1モードです。元アルファと所有マスクを掛け合わせる初期抽出に限り使用し、補完済みの最終パーツへ再適用しません。参照の背景や部品の所有が正しいかは別途目視で確認します。
