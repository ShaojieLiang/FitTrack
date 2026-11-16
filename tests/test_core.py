import copy
from contextlib import closing
from datetime import date,timedelta
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from fittrack.db import connect,history
from fittrack.ingest import ingest
from fittrack.synthetic import generate
from fittrack.model import features,evaluate,forecast,groups
from fittrack.coach import save_forecast,feedback
from fittrack.server import configuration,sync,request

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.tmp.name)/"test.sqlite3")
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def load(self,days=70):
        p=generate(days=days)
        ingest(self.db,p,"synthetic")
        return p
    def test_upsert_and_atomic_validation(self):
        p=self.load()
        old=history(self.db)
        ingest(self.db,p,"synthetic")
        self.assertEqual(old,history(self.db))
        bad=copy.deepcopy(p)
        bad["body"][-1]["value"]=float("nan")
        bad["sessions"][0]["title"]="must roll back"
        with self.assertRaises(ValueError): ingest(self.db,bad,"synthetic")
        self.assertEqual(old,history(self.db))
    def test_unknown_and_unfinished_sets_excluded(self):
        self.load(10)
        comparable,_,_=groups(self.db,"synthetic")
        self.assertEqual(sum(map(len,comparable.values())),10)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sets WHERE kind='work' AND done=1").fetchone()[0],20)
        self.assertEqual(self.db.execute("SELECT sum(duration_seconds) FROM sets WHERE kind='cardio' AND done=1").fetchone()[0],3000)
    def test_first_unfinished_work_set_is_not_replaced_by_later_one(self):
        p=generate(2)
        p["sessions"][0]["movements"][0]["sets"][1]["done"]=False
        ingest(self.db,p,"synthetic")
        comparable,_,_=groups(self.db,"synthetic")
        self.assertEqual(sum(map(len,comparable.values())),1)
    def test_pounds_and_null_measurement_time(self):
        p=generate(2)
        g=p["sessions"][0]["movements"][0]["sets"][1]
        g.update(weight=100,unit="lb")
        p["body"][0]["measured_at"]=None
        ingest(self.db,p,"manual")
        self.assertAlmostEqual(self.db.execute("SELECT weight_kg FROM sets WHERE movement_pos=0 AND position=1").fetchone()[0],45.359237)
        self.assertIsNone(self.db.execute("SELECT measured_at FROM body LIMIT 1").fetchone()[0])
    def test_future_records_cannot_change_past_features(self):
        p=self.load()
        comparable,body,_=groups(self.db,"synthetic")
        rows=list(comparable.values())[0]
        target=rows[10]["day"]
        x=features(rows[:10],target,body)
        body.append({"day":target,"metric":"weight","value":999999})
        body.append({"day":"2099-01-01","metric":"bodyfat","value":999999})
        y=features(rows,target,body)
        np.testing.assert_equal(x,y)
    def test_chronological_evaluation_and_reproducibility(self):
        self.load(70)
        a=evaluate(self.db,"synthetic")
        b=evaluate(self.db,"synthetic")
        self.assertEqual(a,b)
        self.assertGreater(a["test_samples"],0)
        self.assertTrue(all(r["train_cutoff"]<r["day"] for r in a["predictions"]))
        self.assertEqual(set(a["mae_reps"]),{"last","mean3","ridge_training","ridge_body"})
    def test_forecast_immutable_and_feedback_explicit(self):
        self.load(70)
        p=forecast(self.db,"synthetic",("Bench press","demo-flat-bench-A",50.0),"2025-03-12")
        saved=save_forecast(self.db,p,"2025-03-11T20:00:00+08:00")
        changed=dict(p,prediction=99)
        self.assertEqual(save_forecast(self.db,changed,"2025-03-11T21:00:00+08:00")["prediction"],saved["prediction"])
        result=feedback(self.db,saved["id"],9,"2025-03-12")
        self.assertEqual(result["actual"],9)
        self.assertIsNone(result["adopted"])
        with self.assertRaises(ValueError): feedback(self.db,saved["id"],10,"2025-03-12")
        with self.assertRaises(ValueError): save_forecast(self.db,p,"2025-03-12T01:00:00+08:00")
    def test_sparse_history_and_source_isolation(self):
        self.load(8)
        self.assertEqual(forecast(self.db,"synthetic",("Bench press","demo-flat-bench-A",50.0),"2025-02-01")["status"],"insufficient_data")
        self.assertEqual(evaluate(self.db,"manual")["test_samples"],0)
    @patch("fittrack.server.configuration",return_value=("unused", "unused"))
    @patch("fittrack.server.request")
    def test_sync_rejection_leaves_database_unchanged(self,mock,config):
        self.load(2)
        before=history(self.db)
        mock.side_effect=[{"complete":True,"sessions":[]},{"complete":True,"body":[{"day":"2025-01-02"}]}]
        with self.assertRaises(ValueError): sync(self.db,"2025-01-01")
        self.assertEqual(history(self.db),before)
    @patch.dict("os.environ",{},clear=True)
    def test_network_requires_explicit_credentials(self):
        with self.assertRaisesRegex(ValueError,"FITTRACK_BODY_API_URL"):
            request("body",{})
    @patch.dict("os.environ",{},clear=True)
    @patch("fittrack.server.request")
    def test_empty_configuration_prevents_any_sync_request(self,mock):
        with self.assertRaisesRegex(ValueError,"FITTRACK_TRAINING_API_URL"):
            sync(self.db,"2025-01-01")
        mock.assert_not_called()
    @patch.dict("os.environ",{"FITTRACK_BODY_API_URL":"https://body.example.invalid/read","FITTRACK_BODY_TOKEN":"fixture-only"},clear=True)
    def test_user_supplied_endpoint_and_token(self):
        self.assertEqual(configuration("body"),("https://body.example.invalid/read","fixture-only"))
    @patch.dict("os.environ",{"FITTRACK_BODY_API_URL":"file:///private","FITTRACK_BODY_TOKEN":"fixture-only"},clear=True)
    def test_non_http_endpoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"HTTP"):
            configuration("body")
    @patch("fittrack.server.configuration",return_value=("unused", "unused"))
    @patch("fittrack.server.request")
    def test_private_server_contract_imports_normalized_records(self,mock,config):
        fixture=generate(2)
        day="2025-01-01"
        mock.side_effect=[{"complete":True,"sessions":fixture["sessions"]},
                          {"complete":True,"body":[r for r in fixture["body"] if r["day"]==day]}]
        result=sync(self.db,day)
        self.assertEqual(result["source"],"server")
        self.assertEqual(len(history(self.db,source="server")["body"]),2)
    @patch.dict("os.environ",{"FITTRACK_BODY_API_URL":"https://body.example.invalid/read","FITTRACK_BODY_TOKEN":"fixture-only"},clear=True)
    @patch("fittrack.server.urllib.request.build_opener")
    def test_incomplete_response_is_rejected(self,opener):
        opener.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"complete":false,"body":[]}'
        with self.assertRaisesRegex(ValueError,"complete response"):
            request("body",{"date":"2025-01-01"})
    def test_demo_cannot_reset_or_publish_private_records(self):
        from fittrack.cli import demo
        out=Path(self.tmp.name)/"mixed"
        with closing(connect(out/"fittrack.sqlite3")) as db:
            ingest(db,generate(2),"manual")
        dest=Path(self.tmp.name)/"public"
        with self.assertRaisesRegex(ValueError,"non-synthetic"):
            demo(out,dest)
        self.assertFalse(dest.exists())
        with closing(connect(out/"fittrack.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM sessions").fetchone()[0],1)

if __name__=="__main__": unittest.main()
