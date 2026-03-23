#!/usr/bin/env bash
set -euo pipefail

CGROOT="/sys/fs/cgroup"
PARENT="slabvscale.slice"

mkdir -p "${CGROOT}/${PARENT}"

# create child slices for three example functions
for name in func_a.slice func_b.slice func_c.slice; do
  mkdir -p "${CGROOT}/${PARENT}/${name}"
  # enable memory controller if needed (unified cgroup v2 assumed)
  echo "+memory" > "${CGROOT}/cgroup.subtree_control" 2>/dev/null || true
done

echo "Created cgroups under ${CGROOT}/${PARENT}"
