#!/bin/bash

echo "Select a Lambda:"
select dir in $(ls -d * |grep -v "start.sh\|Makefile\|create-or-update-function.sh"); do
  test -n "$dir" && break
  echo ">>> Invalid Selection"
done

# Use symlinks instead of copying to avoid duplication
ln -sf ../Makefile $dir/Makefile 2>/dev/null || true
ln -sf ../create-or-update-function.sh $dir/create-or-update-function.sh 2>/dev/null || true
cd $dir
# make run

echo "Select command:"
select command in run deploy; do
    make $command && break
    echo ">>> Invalid Selection"
done