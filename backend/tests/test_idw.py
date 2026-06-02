from app.idw import interpolate


def test_idw_grid_shape_and_bounds():
    pts = [{"device_id": "a", "lon": 120.00, "lat": 30.00, "value": 10.0},
           {"device_id": "b", "lon": 120.01, "lat": 30.01, "value": 20.0}]
    g = interpolate(pts, nx=10, ny=8)
    assert g["nx"] == 10 and g["ny"] == 8 and len(g["cells"]) == 80
    # IDW 是加权平均，结果必在输入 [min,max] 内
    assert 10.0 <= g["vmin"] and g["vmax"] <= 20.0
    # 每个测点都映射出网格索引
    assert all("i" in p and "j" in p for p in g["points"])


def test_idw_near_point_value():
    pts = [{"device_id": "a", "lon": 120.00, "lat": 30.00, "value": 10.0},
           {"device_id": "b", "lon": 120.02, "lat": 30.02, "value": 30.0}]
    g = interpolate(pts, nx=20, ny=20)
    pa = next(p for p in g["points"] if p["device_id"] == "a")
    cell = next(c for c in g["cells"] if c[0] == pa["i"] and c[1] == pa["j"])
    assert abs(cell[2] - 10.0) < 5.0  # a 附近应接近其测值


def test_idw_single_point_constant():
    g = interpolate([{"device_id": "a", "lon": 120.0, "lat": 30.0, "value": 15.0}], nx=5, ny=5)
    assert g["vmin"] == 15.0 and g["vmax"] == 15.0
