# Add arguments
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--disable-discord-logs', help='Disables Discord logging.', action='store_true')
parser.add_argument('--disable-scheduler-logs', help='Disables scheduler logs.', action='store_true')
args = parser.parse_args()