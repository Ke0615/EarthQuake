import requests
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import json # GeoJSONファイルを読み込むために追加

# --- 設定 ---
# データを取得する期間（現在から遡る日数）。例: 30日前のデータまで取得。
DAYS_AGO = 1000
# 取得する地震の最小マグニチュード。これ未満の地震は除外。
MIN_MAGNITUDE = 2.5
# 取得する地理的範囲の最小緯度。
MIN_LAT = 20
# 取得する地理的範囲の最大緯度。
MAX_LAT = 50
# 取得する地理的範囲の最小経度。
MIN_LON = 120
# 取得する地理的範囲の最大経度。
MAX_LON = 150
# プロットする地震の最小深度（km）。これより浅い地震は表層地震として除外。
MIN_DEPTH_KM = 30
# 3DプロットのX軸（経度）のアスペクト比。
ASPECT_X = 1.0
# 3DプロットのY軸（緯度）のアスペクト比。
ASPECT_Y = 1.0
# 3DプロットのZ軸（深さ）のアスペクト比。この値を大きくすると縦長になる。
ASPECT_Z = 0.3

# 地震マーカーのベースサイズ。マグニチュードが小さい場合の最小サイズとして機能。
EARTHQUAKE_MARKER_SIZE_BASE = 3
# 地震マーカーのサイズをマグニチュードに基づいて調整する倍率。
MARKER_MAGNITUDE_MULTIPLIER = 1.0

# 主要都市マーカーのサイズ。
CITY_MARKER_SIZE = 3

# GeoJSONファイル名
GEOJSON_FILE = 'gadm41_JPN_0.json' # 追加

# 主要な日本の都市のデータ: (緯度, 経度, 都市名) のタプルのリスト。
MAJOR_JAPANESE_CITIES = [
    (35.6895, 139.6917, "東京"),
    (34.6937, 135.5022, "大阪"),
    (35.1815, 136.9066, "名古屋"),
    (43.0621, 141.3544, "札幌"),
    (33.5903, 130.4017, "福岡"),
    (38.2682, 140.8694, "仙台"),
    (34.3963, 132.4596, "広島"),
    (34.6851, 133.9187, "岡山"),
    (38.0000, 140.0000, "福島"),
    (37.9023, 139.0232, "新潟"),
    (35.0116, 135.7681, "京都"),
    (34.7042, 137.3820, "浜松"),
    (32.7875, 129.8738, "長崎"),
    (31.5969, 130.5571, "鹿児島"),
    (26.2124, 127.6809, "那覇")
]
# -----------

def get_usgs_earthquake_data(days_ago, min_magnitude, min_lat, max_lat, min_lon, max_lon):
    """
    USGS地震カタログAPIから地震データを取得する関数。

    Args:
        days_ago (int): 現在から遡ってデータを取得する日数。
        min_magnitude (float): 取得する地震の最小マグニチュード。
        min_lat (float): 取得範囲の最小緯度。
        max_lat (float): 取得範囲の最大緯度。
        min_lon (float): 取得範囲の最小経度。
        max_lon (float): 取得範囲の最大経度。

    Returns:
        list: 取得した地震情報のリスト。各要素は辞書形式。
    """
    # APIリクエストの終了時刻（現在時刻）。
    end_time = datetime.now()
    # APIリクエストの開始時刻（現在時刻からdays_ago分遡る）。
    start_time = end_time - timedelta(days=days_ago)
    # USGS地震カタログAPIのエンドポイントURL。
    api_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    # APIに渡すパラメータを格納した辞書。
    params = {
        "format": "geojson", # データ形式をGeoJSONに指定。
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"), # 検索開始日時。
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),     # 検索終了日時。
        "minmagnitude": min_magnitude, # 最小マグニチュード。
        "minlatitude": min_lat,        # 最小緯度。
        "maxlatitude": max_lat,        # 最大緯度。
        "minlongitude": min_lon,       # 最小経度。
        "maxlongitude": max_lon,       # 最大経度。
        "limit": 20000,                # 1リクエストあたりの最大取得件数。
        "orderby": "time",             # 結果を時間でソート。
    }
    
    print(f"USGS APIから過去{days_ago}日間のM{min_magnitude}以上の地震情報を取得中...")
    try:
        # APIリクエストを実行。
        response = requests.get(api_url, params=params)
        # HTTPエラーが発生した場合に例外を発生させる。
        response.raise_for_status()
        # レスポンスボディをJSON形式でパース。
        data = response.json()
        # 処理済みの地震情報を格納するリスト。
        earthquake_list = []
        # GeoJSONデータ内の各地震イベントをループ処理。
        for feature in data.get('features', []):
            # イベントのプロパティ（マグニチュード、場所、時刻など）。
            properties = feature.get('properties')
            # イベントの地理情報（経度、緯度、深さ）。
            geometry = feature.get('geometry')
            # プロパティと地理情報が存在し、座標データがあることを確認。
            if properties and geometry and geometry.get('coordinates'):
                lon = geometry['coordinates'][0] # 経度。
                lat = geometry['coordinates'][1] # 緯度。
                depth = geometry['coordinates'][2] # 深さ（km）。
                mag = properties.get('mag')      # マグニチュード。
                time_ms = properties.get('time') # Unixミリ秒形式の発生時刻。
                place = properties.get('place')  # 地震の発生場所のテキスト。

                # Unixミリ秒を日時文字列に変換。
                event_time = datetime.fromtimestamp(time_ms / 1000).strftime("%Y/%m/%d %H:%M:%S") if time_ms else "不明"
                # 緯度、経度、深さが有効な数値であり、深さとマグニチュードが存在することを確認。
                if all(isinstance(val, (int, float)) for val in [lat, lon, depth]) and depth is not None and mag is not None:
                    # 指定された最小深度以上の地震のみをリストに追加。
                    if depth >= MIN_DEPTH_KM:
                        earthquake_list.append({
                            'latitude': lat, 'longitude': lon, 'depth': depth,
                            'magnitude': mag, 'time': event_time, 'place': place
                        })
        return earthquake_list
    except requests.exceptions.RequestException as e:
        # APIリクエスト中にエラーが発生した場合、エラーメッセージを表示。
        print(f"APIからのデータ取得中にエラーが発生しました: {e}")
        return []

def extract_geojson_lines(geojson_data):
    """
    GeoJSONデータからすべての線分座標を抽出するヘルパー関数。
    Polygon、MultiPolygon、LineString、MultiLineStringに対応。
    """
    all_lines = []

    def extract_coords(geometry):
        coords = []
        geom_type = geometry.get('type')
        geom_coords = geometry.get('coordinates')

        if geom_type == 'Point':
            # ポイントは線ではないのでスキップ
            pass
        elif geom_type == 'LineString':
            coords.append(geom_coords)
        elif geom_type == 'MultiLineString':
            coords.extend(geom_coords)
        elif geom_type == 'Polygon':
            # ポリゴンの外側のリングのみを線として取得
            coords.append(geom_coords[0])
        elif geom_type == 'MultiPolygon':
            # 複数のポリゴンそれぞれについて外側のリングを取得
            for poly in geom_coords:
                coords.append(poly[0])
        return coords

    # GeoJSON FeatureCollectionの場合
    if geojson_data.get('type') == 'FeatureCollection':
        for feature in geojson_data.get('features', []):
            geometry = feature.get('geometry')
            if geometry:
                all_lines.extend(extract_coords(geometry))
    # GeoJSON Featureの場合
    elif geojson_data.get('type') == 'Feature':
        geometry = geojson_data.get('geometry')
        if geometry:
            all_lines.extend(extract_coords(geometry))
    # GeoJSON Geometryの場合
    elif 'coordinates' in geojson_data and 'type' in geojson_data:
        all_lines.extend(extract_coords(geojson_data))
    
    return all_lines

def visualize_earthquakes_pure_3d(earthquakes_data):
    """
    取得した地震データを3Dで可視化する関数。

    Args:
        earthquakes_data (list): get_usgs_earthquake_data関数から返された地震情報のリスト。
    """
    if not earthquakes_data:
        print("可視化する地震情報がありません。")
        return

    print(f"可視化対象の有効な地震データ数: {len(earthquakes_data)}件")
    latitudes, longitudes, depths_for_plot, depths_original, magnitudes, event_details = [], [], [], [], [], []

    for eq in earthquakes_data:
        latitudes.append(eq['latitude'])
        longitudes.append(eq['longitude'])
        depths_original.append(eq['depth'])
        depths_for_plot.append(-eq['depth']) # 深さはZ軸で下向きに表現するため負の値にする。
        magnitudes.append(eq['magnitude'])

        detail_text = (
            f"発生時刻: {eq['time']}<br>"
            f"震源: {eq['place']}<br>"
            f"緯度: {eq['latitude']}<br>"
            f"経度: {eq['longitude']}<br>"
            f"深さ: {eq['depth']} km<br>"
            f"マグニチュード: {eq['magnitude']}"
        )
        event_details.append(detail_text)

    marker_sizes = [max(EARTHQUAKE_MARKER_SIZE_BASE, (mag * MARKER_MAGNITUDE_MULTIPLIER)) for mag in magnitudes]

    data_to_plot = [
        go.Scatter3d(
            x=longitudes, y=latitudes, z=depths_for_plot,
            mode='markers',
            marker=dict(
                size=marker_sizes,
                color=depths_original,
                colorscale='Viridis',
                reversescale=True,
                opacity=0.7,
                colorbar=dict(title='深さ (km)', lenmode='fraction', len=0.7, x=0.05, y=0.7),
                line_color='rgba(0,0,0,0.3)',
                line_width=0.5
            ),
            text=event_details, hoverinfo='text',
            name='Earthquakes'
        )
    ]

    # 主要都市をプロット（Z=0に固定）
    city_lats = [city[0] for city in MAJOR_JAPANESE_CITIES]
    city_lons = [city[1] for city in MAJOR_JAPANESE_CITIES]
    city_names = [city[2] for city in MAJOR_JAPANESE_CITIES]
    city_zs = [0] * len(MAJOR_JAPANESE_CITIES)

    data_to_plot.append(
        go.Scatter3d(
            x=city_lons, y=city_lats, z=city_zs,
            mode='markers+text',
            marker=dict(
                size=CITY_MARKER_SIZE,
                color='black',
                symbol='circle',
            ),
            text=city_names,
            textfont=dict(
                color='black',
                size=10
            ),
            textposition='top center',
            hoverinfo='text',
            name='Major Cities'
        )
    )

    # --- GeoJSONファイルの読み込みとプロット ---
    try:
        with open(GEOJSON_FILE, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        # GeoJSONデータから線分を抽出
        map_lines = extract_geojson_lines(geojson_data)
        print(f"GeoJSONファイル '{GEOJSON_FILE}' から {len(map_lines)} 個の線分を抽出しました。")

        # 各線分をPlotlyのトレースとして追加
        for i, line_coords in enumerate(map_lines):
            # 経度と緯度を分離
            line_lons = [coord[0] for coord in line_coords]
            line_lats = [coord[1] for coord in line_coords]
            # Z座標は地表(0)に固定
            line_zs = [0] * len(line_coords)

            data_to_plot.append(go.Scatter3d(
                x=line_lons, y=line_lats, z=line_zs,
                mode='lines',
                line=dict(color='gray', width=1), # 地図の線の色と太さを調整
                showlegend=False, # 凡例に表示しない
                hoverinfo='none', # マウスオーバー情報を表示しない
                name=f'GeoJSON_Map_Line_{i}' # トレース名 (内部用)
            ))
        print("GeoJSONの線分をプロットに追加しました。")

    except FileNotFoundError:
        print(f"エラー: GeoJSONファイル '{GEOJSON_FILE}' が見つかりません。")
    except json.JSONDecodeError:
        print(f"エラー: GeoJSONファイル '{GEOJSON_FILE}' の形式が不正です。")
    except Exception as e:
        print(f"GeoJSONの読み込みまたは処理中にエラーが発生しました: {e}")
    # --- GeoJSONのプロットここまで ---


    fig = go.Figure(data=data_to_plot)

    fig.update_layout(
        title=f'USGS地震カタログ - 過去{DAYS_AGO}日間のM{MIN_MAGNITUDE}以上、深さ{MIN_DEPTH_KM}km以上の地震 3D可視化 (GeoJSON地図と主要都市表示)',
        scene=dict(
            xaxis_title='経度',
            yaxis_title='緯度',
            zaxis_title='深さ (km)',
            aspectmode='manual',
            aspectratio=dict(x=ASPECT_X, y=ASPECT_Y, z=ASPECT_Z),
            camera=dict(eye=dict(x=-1.5, y=-1.5, z=0.5))
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    fig.show()

    output_filename = "earthquake_map.html"
    fig.write_html(output_filename, include_plotlyjs='cdn')
    print(f"グラフが '{output_filename}' として保存されました。")

if __name__ == "__main__":
    usgs_earthquake_data = get_usgs_earthquake_data(
        days_ago=DAYS_AGO, min_magnitude=MIN_MAGNITUDE,
        min_lat=MIN_LAT, max_lat=MAX_LAT, min_lon=MIN_LON, max_lon=MAX_LON
    )
    if usgs_earthquake_data:
        print(f"USGS APIから{len(usgs_earthquake_data)}件の有効な地震データを受信しました。3D可視化を開始します。")
        visualize_earthquakes_pure_3d(usgs_earthquake_data)
    else:
        print("地震情報の取得に失敗したか、利用可能な情報がありませんでした。")