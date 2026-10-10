#!/bin/bash
# Usage : run-headless.sh <import|process> [postScript args...]
set -e
T="C:/Users/Thisma/Documents/Switch/tools-re"
export JAVA_HOME="$T/jdk"
export PATH="$JAVA_HOME/bin:$PATH"
H="$T/ghidra/support/analyzeHeadless.bat"
mode=$1; shift
if [ "$mode" = import ]; then
  cmd //c "$H" "$T/ghidra-proj" rosa -import "$T/rosa-or/code.bin" -loader BinaryLoader -loader-baseAddr 0x00100000 -processor ARM:LE:32:v6 -cspec default -scriptPath "$T/ghidra-scripts" -preScript CtrLayout.java 0x00630000 0x7EC2C -analysisTimeoutPerFile 7200 "$@"
else
  cmd //c "$H" "$T/ghidra-proj" rosa -process code.bin -noanalysis -scriptPath "$T/ghidra-scripts" "$@"
fi
