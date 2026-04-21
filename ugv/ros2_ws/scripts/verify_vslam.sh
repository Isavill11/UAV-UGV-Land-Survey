#!/usr/bin/env bash
# verify_vslam.sh
#
# Smoke-test script for the UGV VSLAM bring-up.
# Checks that the key topics are publishing and the TF tree is complete.
#
# Prerequisites:
#   - ROS 2 Jazzy is sourced (and the workspace install overlay)
#   - ugv_vslam.launch.py is already running in another terminal
#
# Usage:
#   ./scripts/verify_vslam.sh
#   ./scripts/verify_vslam.sh --timeout 15   # wait up to 15 s per check

set -euo pipefail

# ── Helpers ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GRN}[PASS]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; FAILURES=$((FAILURES + 1)); }
info() { echo -e "${YEL}[INFO]${NC} $*"; }

FAILURES=0
TIMEOUT=${2:-10}   # seconds to wait for each topic / TF check

# ── Source ROS 2 ──────────────────────────────────────────────────────────
if [ -z "${ROS_DISTRO:-}" ]; then
    # shellcheck disable=SC1091
    source /opt/ros/jazzy/setup.bash
fi

# Source workspace overlay if available (native build)
WS_INSTALL="$(cd "$(dirname "$0")/.." && pwd)/install/setup.bash"
if [ -f "${WS_INSTALL}" ]; then
    # shellcheck disable=SC1090
    source "${WS_INSTALL}"
    info "Sourced workspace overlay: ${WS_INSTALL}"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  UGV VSLAM Verification  –  ROS 2 ${ROS_DISTRO}"
echo "════════════════════════════════════════════════════════"
echo ""

# ── 1. Node presence ───────────────────────────────────────────────────────
info "Checking for running RTAB-Map nodes …"

for node in /rgbd_odometry /rtabmap /rgbd_sync; do
    if ros2 node list 2>/dev/null | grep -q "^${node}$"; then
        pass "Node ${node} is alive"
    else
        fail "Node ${node} NOT found (is ugv_vslam.launch.py running?)"
    fi
done

# ── 2. Topic frequency checks ─────────────────────────────────────────────
info "Checking topic publication rates (${TIMEOUT} s window) …"

check_topic_hz() {
    local topic="$1"
    local min_hz="$2"

    # ros2 topic hz prints something like "average rate: 29.9"
    local rate
    rate=$(timeout "${TIMEOUT}" ros2 topic hz --window 5 "${topic}" 2>/dev/null \
           | grep "average rate" | awk '{print $3}' | tr -d ':' | head -1)

    if [ -z "${rate}" ]; then
        fail "${topic}: no messages received within ${TIMEOUT} s"
        return
    fi

    # Use awk for floating-point comparison
    if awk "BEGIN { exit !(${rate} >= ${min_hz}) }"; then
        pass "${topic}: ${rate} Hz  (min: ${min_hz} Hz)"
    else
        fail "${topic}: ${rate} Hz is below minimum ${min_hz} Hz"
    fi
}

# RealSense colour stream
check_topic_hz "/camera/camera/color/image_raw"                     25
# RealSense aligned depth stream
check_topic_hz "/camera/camera/aligned_depth_to_color/image_raw"   25
# Visual odometry output (RTAB-Map publishes at ~camera rate)
check_topic_hz "/rtabmap/odom"                                       5

# ── 3. Topic existence (low-rate or latched) ──────────────────────────────
info "Checking for map topics …"

for topic in /rtabmap/map /rtabmap/grid_map /rtabmap/mapData; do
    if timeout "${TIMEOUT}" ros2 topic echo --once "${topic}" \
           > /dev/null 2>&1; then
        pass "Topic ${topic} received at least one message"
    else
        fail "Topic ${topic}: no message within ${TIMEOUT} s (may be normal early on)"
    fi
done

# ── 4. TF tree validation ──────────────────────────────────────────────────
info "Checking TF tree: map → odom → base_link …"

check_tf() {
    local parent="$1"
    local child="$2"

    if timeout "${TIMEOUT}" ros2 run tf2_ros tf2_echo "${parent}" "${child}" \
           > /dev/null 2>&1; then
        pass "TF: ${parent} → ${child} is broadcasting"
    else
        fail "TF: ${parent} → ${child} NOT found within ${TIMEOUT} s"
    fi
}

check_tf "map"  "odom"
check_tf "odom" "base_link"
check_tf "map"  "base_link"   # transitive – verifies full chain

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
if [ "${FAILURES}" -eq 0 ]; then
    echo -e "${GRN}All checks passed.${NC}  VSLAM bring-up looks healthy."
else
    echo -e "${RED}${FAILURES} check(s) failed.${NC}  Review output above."
fi
echo "════════════════════════════════════════════════════════"
echo ""

exit "${FAILURES}"
