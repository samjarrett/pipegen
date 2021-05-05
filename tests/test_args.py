from pipegen import args


def test_split_key_val_pairs():
    """Tests split_key_val_pairs()"""
    assert args.split_key_val_pairs(None, None, ["Key=Value", "KeyTwo=Value2"]) == {
        "Key": "Value",
        "KeyTwo": "Value2",
    }
    assert args.split_key_val_pairs(None, None, ["Lorem=Ipsum", "Dolor=SitAmet"]) == {
        "Lorem": "Ipsum",
        "Dolor": "SitAmet",
    }
