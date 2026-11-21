"""End-to-end live simulation streaming test.csv rows through rt_prediction -> Node-RED."""

import argparse
from datetime import datetime
import itertools
import json
import os
import signal
import tempfile
import threading
import time
import urllib.request
import uuid
import pandas as pd
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from sklearn.metrics import accuracy_score, f1_score

import case_config as cfg
import rt_prediction as rt

NODERED_URL = "http://127.0.0.1:1880/flows"
BROKER_SIM = "broker.emqx.io"
BROKER_PORT = 1883
NODE_BROKER_ID = "7b749cbd3b1d96e1"
NODE_MQTT_IN_ID = "dcbc3657a30ccb74"
DEFAULT_RESTORE_BROKER = "192.168.1.1"
DEFAULT_RESTORE_TOPIC = rt.MQTT_CONFIG["TOPIC_OUT"]


def get_nodered_flows():
    """Fetch current Node-RED flow configuration array."""
    req = urllib.request.Request(NODERED_URL, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_nodered_nodes(flows):
    """Deploy modified Node-RED nodes without wiping dashboard chart/gauge state."""
    data = json.dumps(flows).encode("utf-8")
    req = urllib.request.Request(
        NODERED_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Node-RED-Deployment-Type": "nodes",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def parse_args():
    """Parse CLI options for finite or continuous simulation."""
    parser = argparse.ArgumentParser(description="Simulate live MQTT competition feed to Node-RED.")
    parser.add_argument("--loop", action="store_true", help="Stream continuously in an endless loop.")
    parser.add_argument("--interval", type=float, default=None, help="Seconds between rows (default: 1.0 in --loop, 0.8 otherwise).")
    parser.add_argument("--rows", type=int, default=500, help="Number of rows to stream in finite mode.")
    return parser.parse_args()


def main():
    args = parse_args()
    interval_sec = args.interval if args.interval is not None else (1.0 if args.loop else 0.8)

    stop_event = threading.Event()

    def handle_stop(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    run_id = uuid.uuid4().hex[:8]
    topic_in = f"idt/sim/g3b/{run_id}/in"
    topic_out = f"idt/sim/g3b/{run_id}/out"

    flows = get_nodered_flows()
    broker_node = next((n for n in flows if n.get("id") == NODE_BROKER_ID), None)
    mqtt_in_node = next((n for n in flows if n.get("id") == NODE_MQTT_IN_ID), None)
    if broker_node is None or mqtt_in_node is None:
        raise RuntimeError(
            f"Expected Node-RED nodes {NODE_BROKER_ID} / {NODE_MQTT_IN_ID} not found."
        )

    raw_broker = broker_node.get("broker", DEFAULT_RESTORE_BROKER)
    raw_topic = mqtt_in_node.get("topic", DEFAULT_RESTORE_TOPIC)
    orig_broker = DEFAULT_RESTORE_BROKER if raw_broker == BROKER_SIM else raw_broker
    orig_topic = DEFAULT_RESTORE_TOPIC if str(raw_topic).startswith("idt/sim/") else raw_topic

    tmp_fd, tmp_csv = tempfile.mkstemp(prefix="sim_p2_", suffix=".csv")
    os.close(tmp_fd)

    rt_client = None
    pub_client = None
    switched_nodered = False

    try:
        # 1. Temporarily point Node-RED to broker.emqx.io + sim output topic
        broker_node["broker"] = BROKER_SIM
        mqtt_in_node["topic"] = topic_out
        status = post_nodered_nodes(flows)
        switched_nodered = True
        print(
            f"[Node-RED] Temporarily switched ({status}): "
            f"{orig_broker} -> {BROKER_SIM}, topic -> {topic_out}",
            flush=True,
        )
        time.sleep(2.5)

        # 2. Configure rt_prediction in memory using temp CSV
        rt.MQTT_CONFIG["BROKER_HOST"] = BROKER_SIM
        rt.MQTT_CONFIG["BROKER_PORT"] = BROKER_PORT
        rt.MQTT_CONFIG["TOPIC_IN"] = topic_in
        rt.MQTT_CONFIG["TOPIC_OUT"] = topic_out
        rt.OUTPUT_CSV = tmp_csv
        rt.START_NEW_CSV = True
        rt.error_count = 0
        rt.last_seen_at = None
        rt.connected.clear()
        rt.connect_failure["reason"] = None

        rt.model = rt.load_model()
        rt.prepare_output_csv()

        subscribed_ev = threading.Event()

        def on_sub_wrapper(client, userdata, mid, reason_code_list, properties):
            rt.on_subscribe(client, userdata, mid, reason_code_list, properties)
            if not reason_code_list[0].is_failure:
                subscribed_ev.set()

        rt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sim-rt-{run_id}",
            protocol=mqtt.MQTTv5,
        )
        rt_client.on_connect = rt.on_connect
        rt_client.on_subscribe = on_sub_wrapper
        rt_client.on_message = rt.on_message

        props = Properties(PacketTypes.CONNECT)
        props.SessionExpiryInterval = 60
        rt_client.connect(BROKER_SIM, BROKER_PORT, keepalive=60, clean_start=True, properties=props)
        rt_client.loop_start()

        if not rt.connected.wait(15) or rt.connect_failure["reason"]:
            raise RuntimeError(f"rt_client connect failed: {rt.connect_failure['reason']}")
        if not subscribed_ev.wait(10):
            raise RuntimeError("rt_client did not confirm subscription in time.")

        # 3. Connect publisher client and stream rows from data/test.csv
        pub_connected = threading.Event()
        pub_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sim-pub-{run_id}",
            protocol=mqtt.MQTTv5,
        )

        def on_pub_connect(client, userdata, flags, reason_code, properties):
            if not reason_code.is_failure:
                pub_connected.set()

        pub_client.on_connect = on_pub_connect
        pub_client.connect(BROKER_SIM, BROKER_PORT, keepalive=60, clean_start=True)
        pub_client.loop_start()
        if not pub_connected.wait(15):
            raise RuntimeError("Publisher client could not connect to broker.emqx.io.")

        test_df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "test.csv"))

        if args.loop:
            print(f"[Sim] Continuous loop mode started ({interval_sec:.2f}s/row) -> {topic_in}. Stop task to end.", flush=True)
            records = test_df.to_dict("records")
            last_epoch = 0
            sent_count = 0
            for row in itertools.cycle(records):
                if stop_event.is_set():
                    break
                now_epoch = max(int(time.time()), last_epoch + 1)
                last_epoch = now_epoch
                payload = {
                    "timestamp": datetime.fromtimestamp(now_epoch).strftime("%Y-%m-%d %H:%M:%S"),
                    "temp_c": float(row["temp_c"]),
                    "humidity_pct": float(row["humidity_pct"]),
                    "lux_lm": float(row["lux_lm"]),
                    "co2_ppm": float(row["co2_ppm"]),
                }
                info = pub_client.publish(topic_in, json.dumps(payload), qos=1)
                info.wait_for_publish(timeout=5)
                sent_count += 1
                if len(rt.seen_timestamps) > 200:
                    rt.seen_timestamps.clear()
                if sent_count % 500 == 0:
                    rt.prepare_output_csv()
                if stop_event.wait(interval_sec):
                    break
        else:
            sim_df = test_df.head(args.rows).copy()
            print(f"[Sim] Streaming {len(sim_df)} rows from data/test.csv -> {topic_in} ({interval_sec:.2f}s/row)...", flush=True)

            last_info = None
            for sent_i, (_, row) in enumerate(sim_df.iterrows(), 1):
                if stop_event.is_set():
                    break
                payload = {
                    "timestamp": str(row["timestamp"]),
                    "temp_c": float(row["temp_c"]),
                    "humidity_pct": float(row["humidity_pct"]),
                    "lux_lm": float(row["lux_lm"]),
                    "co2_ppm": float(row["co2_ppm"]),
                }
                last_info = pub_client.publish(topic_in, json.dumps(payload), qos=1)
                if sent_i % 25 == 0:
                    last_info.wait_for_publish(timeout=10)
                if interval_sec > 0 and stop_event.wait(interval_sec):
                    break

            if last_info is not None:
                last_info.wait_for_publish(timeout=10)

            deadline = time.time() + 15.0
            while len(rt.seen_timestamps) < len(sim_df) and time.time() < deadline:
                time.sleep(0.2)
            time.sleep(1.0)

            pred_df = pd.read_csv(tmp_csv)
            merged = sim_df[["timestamp", "y", "y_label"]].merge(
                pred_df[["timestamp", "y_pred", "y_label_pred"]],
                on="timestamp",
                how="inner",
            )
            acc = accuracy_score(merged["y"], merged["y_pred"]) if len(merged) else 0.0
            f1 = f1_score(merged["y"], merged["y_pred"], average="macro", labels=cfg.class_ids(), zero_division=0) if len(merged) else 0.0
            counts = pred_df["y_label_pred"].value_counts().to_dict() if len(pred_df) else {}

            print("=" * 60, flush=True)
            print(f"Simulation Summary : sent={len(sim_df)} | predicted={len(pred_df)} | errors={rt.error_count}", flush=True)
            print(f"Matched rows       : {len(merged)}/{len(sim_df)}", flush=True)
            print(f"Sample Accuracy    : {acc:.4f} | Macro-F1: {f1:.4f}", flush=True)
            print(f"Predicted classes  : {counts}", flush=True)
            print("=" * 60, flush=True)

    finally:
        for cli in (pub_client, rt_client):
            if cli is not None:
                try:
                    cli.disconnect()
                    cli.loop_stop()
                except Exception:
                    pass

        if os.path.exists(tmp_csv):
            try:
                os.remove(tmp_csv)
            except Exception:
                pass

        if switched_nodered:
            restore_flows = get_nodered_flows()
            b_node = next((n for n in restore_flows if n.get("id") == NODE_BROKER_ID), None)
            m_node = next((n for n in restore_flows if n.get("id") == NODE_MQTT_IN_ID), None)
            if b_node is not None and m_node is not None:
                b_node["broker"] = orig_broker
                m_node["topic"] = orig_topic
                post_nodered_nodes(restore_flows)
            verify_flows = get_nodered_flows()
            vb = next(n for n in verify_flows if n.get("id") == NODE_BROKER_ID)
            vm = next(n for n in verify_flows if n.get("id") == NODE_MQTT_IN_ID)
            print(
                f"[Node-RED] Restored: broker={vb['broker']} | topic={vm['topic']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
