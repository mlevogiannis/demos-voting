#!/bin/sh

rm -f crypto_pb2.py

DST_DIR="$(realpath ../../../../)"
SRC_DIR="$DST_DIR/$(realpath --relative-to=$DST_DIR .)"

protoc --proto_path="$DST_DIR" --python_out="$DST_DIR" "$SRC_DIR/crypto.proto"


# python 2 and 3 compatible, if protobuf < 3.0.0

PROTOC_VERSION=$(protoc --version | sed 's/[^0-9]//g')

if [ $PROTOC_VERSION -lt 300 ]
then
    sed -i '1s;^;from django.utils import six\n\n;' crypto_pb2.py
    sed -i 's/unicode("\(.*\)", "utf-8")/six\.text_type(b"\1", "utf-8")/g' crypto_pb2.py
    sed -i 'N;s/\( *\)\(.*\)\n\ *__metaclass__ *= *\(.*\)/\1@six.add_metaclass(\3)\n\1\2/' crypto_pb2.py
fi

