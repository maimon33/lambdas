#!/bin/bash

echo "Select a Lambda:"
# List directories, but put README.md last
DIRS=$(ls -d * | grep -v "start.sh\|Makefile\|create-or-update-function.sh\|README.md")
if [ -f "README.md" ]; then
    DIRS="$DIRS README.md"
fi
select dir in $DIRS; do
  test -n "$dir" && break
  echo ">>> Invalid Selection"
done

# Only create symlinks if Makefile doesn't exist (don't overwrite custom ones)
if [ ! -f "$dir/Makefile" ]; then
    ln -sf ../Makefile $dir/Makefile 2>/dev/null || true
fi
if [ ! -f "$dir/create-or-update-function.sh" ]; then
    ln -sf ../create-or-update-function.sh $dir/create-or-update-function.sh 2>/dev/null || true
fi
cd $dir

echo "Select command:"
# Detect main commands from Makefile - look for setup, run, deploy, update
COMMANDS=""
if grep -q "^setup:" Makefile 2>/dev/null; then
    COMMANDS="$COMMANDS setup"
fi
if grep -q "^run:" Makefile 2>/dev/null; then
    COMMANDS="$COMMANDS run"
fi
if grep -q "^deploy:" Makefile 2>/dev/null; then
    COMMANDS="$COMMANDS deploy"
fi
if grep -q "^update:" Makefile 2>/dev/null; then
    COMMANDS="$COMMANDS update"
fi
if grep -q "^delete:" Makefile 2>/dev/null; then
    COMMANDS="$COMMANDS delete"
fi

# Default if no commands found
if [ -z "$COMMANDS" ]; then
    COMMANDS="run deploy"
fi

select command in $COMMANDS; do
    make $command && break
    echo ">>> Invalid Selection"
done