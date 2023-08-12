#!/usr/bin/env python3

import argparse
import json
import sys
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_public_ip():
    try:
        ip = requests.get("https://api.ipify.org").text.strip()
    except requests.RequestException:
        ip = requests.get("https://ipv4.icanhazip.com/").text.strip()
    return ip


def changer(auth_email, auth_method, auth_key, zone_identifier, record_name, proxy):
    ip = get_public_ip()

    if not ip:
        logger.error("DDNS Updater: No public IP found")
        return

    response = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records?name={record_name}",
        headers={"X-Auth-Email": auth_email, "X-Auth-Key": auth_key, "Content-Type": "application/json"},
    )
    record_data = response.json()

    if record_data.get("result_info", {}).get("count", 0) == 0:
        logger.error(f"DDNS Updater: Record does not exist, perhaps create one first? ({ip} for {record_name})")
        return

    old_ip = record_data["result"][0]["content"]
    if ip == old_ip:
        logger.info(f"DDNS Updater: IP ({ip}) for {record_name} has not changed.")
        return

    record_identifier = record_data["result"][0]["id"]

    update_payload = {
        "id": zone_identifier,
        "type": "A",
        "proxied": proxy,
        "name": record_name,
        "content": ip,
    }

    response = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_identifier}/dns_records/{record_identifier}",
        headers={"X-Auth-Email": auth_email, "X-Auth-Key": auth_key, "Content-Type": "application/json"},
        json=update_payload,
    )

    if "success" in response.text:
        logger.info(f"DDNS Updater: {ip} {record_name} DDNS updated.")
    else:
        logger.error(f"DDNS Updater: {ip} {record_name} DDNS failed for {record_identifier} ({ip}). DUMPING RESULTS:\n{response.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process data with arguments")

    parser.add_argument("--auth_email", type=str, required=True, help="Authentication email")
    parser.add_argument("--auth_key", type=str, required=True, help="Authentication key")
    parser.add_argument("--zone_identifier", type=str, required=True, help="Zone identifier")
    parser.add_argument("--auth_method", type=str, default="global", help="Authentication method (default: global)")
    parser.add_argument("--json_file", type=str, required=True, help="Path to JSON file")

    args = parser.parse_args()

    auth_email = args.auth_email
    auth_method = args.auth_method
    auth_key = args.auth_key
    zone_identifier = args.zone_identifier

    try:
        records = json.load(open(args.json_file, "r"))
    except json.JSONDecodeError:
        logger.error("Error on decoding the file provided.")
        sys.exit(1)

    for record in records:
        changer(auth_email, auth_method, auth_key, zone_identifier, record.get("record", ""), record.get("proxy", ""))
