#!/usr/bin/python3
import hashlib
import requests
from requests.auth import HTTPDigestAuth
import os
from urllib.parse import urlparse
import re
import argparse
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Function to compute the hash of a file
def get_file_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Function to parse entries from the m3u file
def parse_m3u(content):
    streams = {}
    lines = content.splitlines()
    current_stream = None

    for line in lines:
        if line.startswith("#EXTINF"):
            # Parse the name from the EXTINF line (everything after the last comma)
            match = re.search(r'^#EXTINF.*,(.*)$', line)
            if match:
                current_stream = match.group(1).strip()
                streams[current_stream] = {"metadata": line, "pipe": None}
        elif line.startswith("pipe://") and current_stream:
            # Save the full pipe:// line
            streams[current_stream]["pipe"] = line
            current_stream = None

    return streams

# Function to fetch the list of networks
def get_networks(tvheadend_url, username, password):
    response = requests.get(f"http://{tvheadend_url}/api/mpegts/network/grid?limit=999999", auth=HTTPDigestAuth(username, password))
    response.raise_for_status()
    return response.json()["entries"]

# Function to fetch the list of muxes
def get_muxes(tvheadend_url, username, password):
    response = requests.get(f"http://{tvheadend_url}/api/mpegts/mux/grid?limit=999999", auth=HTTPDigestAuth(username, password))
    response.raise_for_status()
    return response.json()["entries"]

# Function to compare changes between m3u and muxes
def compare_m3u_with_muxes(m3u_streams, muxes, network_uuid):
    m3u_streams_set = set(m3u_streams.keys())
    mux_streams = {mux["iptv_sname"]: mux for mux in muxes if mux.get("network_uuid") == network_uuid}
    mux_streams_set = set(mux_streams.keys())

    added_streams = m3u_streams_set - mux_streams_set
    removed_streams = mux_streams_set - m3u_streams_set
    common_streams = m3u_streams_set & mux_streams_set

    modified_streams = []
    for stream_name in common_streams:
        m3u_pipe = m3u_streams[stream_name]["pipe"]
        mux_pipe = mux_streams[stream_name]["iptv_url"]
        if m3u_pipe != mux_pipe:
            modified_streams.append((stream_name, m3u_pipe, mux_pipe))

    results = []
    if added_streams:
        results.append("Added streams:")
        for stream_name in added_streams:
            results.append(f"+ {stream_name}: {m3u_streams[stream_name]['pipe']}")

    if removed_streams:
        results.append("Removed streams:")
        for stream_name in removed_streams:
            results.append(f"- {stream_name}: {mux_streams[stream_name]['iptv_url']}")

    if modified_streams:
        results.append("Modified streams:")
        for stream_name, m3u_pipe, mux_pipe in modified_streams:
            results.append(f"* {stream_name} changed:\n  M3U: {m3u_pipe}\n  Mux: {mux_pipe}")

    if not added_streams and not removed_streams and not modified_streams:
        results.append("No changes detected.")

    return "\n".join(results)

# Function to send email
def send_email(smtp_server, smtp_port, sender_email, recipient_email, smtp_username, smtp_password, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())

        print(f"{datetime.now().isoformat()}: Email sent successfully.")
    except Exception as e:
        print(f"{datetime.now().isoformat()}: Failed to send email: {e}")

def monitor_file_changes(tvheadend_url, username, password, email_config):
    networks = get_networks(tvheadend_url, username, password)
    muxes = get_muxes(tvheadend_url, username, password)

    all_results = []

    for network in networks:
        playlist_url = network.get("url")
        network_uuid = network.get("uuid")
        network_name = network.get("networkname", network_uuid)

        if playlist_url and playlist_url.endswith(".m3u"):
            print(f"{datetime.now().isoformat()}: Checking playlist of network '{network_name}': {playlist_url}")

            try:
                response = requests.get(playlist_url, timeout=10)
                response.raise_for_status()
                m3u_content = response.text
                m3u_streams = parse_m3u(m3u_content)

                results = compare_m3u_with_muxes(m3u_streams, muxes, network_uuid)
                print(f"{datetime.now().isoformat()}: {results}")
                all_results.append(f"Results for playlist {playlist_url}:\n{results}\n")
            except requests.RequestException as e:
                error_message = f"{datetime.now().isoformat()}: Error fetching playlist {playlist_url}: {e}"
                print(error_message)
                all_results.append(error_message)

    if email_config:
        # create mail body
        email_body = "Summary:\n---------------------------------------------------------------------------------------------------------\n"
        for block in all_results:
            for line in block.split('\n'):
                if line and line.strip()[0] in ('*', '+', '-'):
                    email_body += line.split(':')[0] + "\n"
        email_body += "\n"
        email_body += "Details:\n---------------------------------------------------------------------------------------------------------\n" + "\n".join(all_results)

        send_email(
            smtp_server=email_config["smtp_server"],
            smtp_port=email_config["smtp_port"],
            sender_email=email_config["sender_email"],
            recipient_email=email_config["recipient_email"],
            smtp_username=email_config["smtp_username"],
            smtp_password=email_config["smtp_password"],
            subject="TVHeadend M3U Comparison Results",
            body=email_body
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compares an M3U file with TVHeadend muxes.")
    parser.add_argument("-s", "--server", required=True, help="TVHeadend server address and port (e.g., 127.0.0.1:9981)")
    parser.add_argument("-user", "--username", required=True, help="Username for TVHeadend authentication")
    parser.add_argument("-pass", "--password", required=True, help="Password for TVHeadend authentication")
    parser.add_argument("--smtp-server", help="SMTP server address for sending email notifications")
    parser.add_argument("--smtp-port", type=int, default=465, help="SMTP server port (default: 465)")
    parser.add_argument("--sender-email", help="Sender email address for email notifications")
    parser.add_argument("--recipient-email", help="Recipient email address for email notifications")
    parser.add_argument("--smtp-username", help="SMTP username for email authentication")
    parser.add_argument("--smtp-password", help="SMTP password for email authentication")
    args = parser.parse_args()

    email_config = None
    if args.smtp_server and args.sender_email and args.recipient_email and args.smtp_username and args.smtp_password:
        email_config = {
            "smtp_server": args.smtp_server,
            "smtp_port": args.smtp_port,
            "sender_email": args.sender_email,
            "recipient_email": args.recipient_email,
            "smtp_username": args.smtp_username,
            "smtp_password": args.smtp_password
        }
    try:
        monitor_file_changes(args.server, args.username, args.password, email_config)
    except KeyboardInterrupt:
        print("Execution was interrupted by signal.")
    except Exception as e:
        print(f"Error during execution: {e}")
