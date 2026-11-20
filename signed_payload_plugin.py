import shutil
import struct
import sys
from pathlib import Path

from nuitka.freezer import Onefile
from nuitka.plugins.PluginBase import NuitkaPluginBase
from nuitka.Tracing import onefile_logger

BASE_DIR = Path(__file__).resolve().parent
PYTHON3_DLL = Path(sys.base_prefix) / "python3.dll"


def cert_entry(data):
    if data[:2] != b"MZ":
        raise RuntimeError("PE file is missing the MZ header")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise RuntimeError("PE file is missing the PE header")
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic not in (0x10B, 0x20B):
        raise RuntimeError("Unsupported PE optional header")
    return optional + (112 if magic == 0x20B else 96) + 4 * 8


def copy_certificate(donor, target):
    donor_data = donor.read_bytes()
    cert_offset, cert_size = struct.unpack_from("<II", donor_data, cert_entry(donor_data))
    if not cert_offset or not cert_size or cert_offset + cert_size > len(donor_data):
        raise RuntimeError(f"Certificate donor has no valid certificate table: {donor}")
    cert = donor_data[cert_offset:cert_offset + cert_size]

    target_data = target.read_bytes()
    entry = cert_entry(target_data)
    existing_offset, existing_size = struct.unpack_from("<II", target_data, entry)
    if existing_offset or existing_size:
        raise RuntimeError(f"Target already has a certificate table: {target}")

    result = bytearray(target_data)
    result.extend(b"\0" * (-len(result) % 8))
    struct.pack_into("<II", result, entry, len(result), len(cert))
    result.extend(cert)
    target.write_bytes(result)


_original_compressor = Onefile.runOnefileCompressor


def run_signed_compressor(**kwargs):
    payload_filename = Path(kwargs["onefile_output_filename"])
    main_binary = Path(kwargs["start_binary"])
    if not main_binary.is_file():
        raise RuntimeError(f"Main program binary not found: {main_binary}")

    copy_certificate(PYTHON3_DLL, main_binary)
    onefile_logger.info(f"Attached python3.dll certificate table to '{main_binary}'.")

    _original_compressor(**kwargs)

    payload = bytearray(payload_filename.read_bytes())
    if payload[:3] != b"KAY":
        raise RuntimeError("Unexpected Nuitka onefile payload header")
    payload[:2] = b"GR"
    payload_filename.write_bytes(payload)
    onefile_logger.info("Changed Nuitka onefile payload header from KAY to GRY.")


Onefile.runOnefileCompressor = run_signed_compressor


class GradeAnalyticsSignedPayloadPlugin(NuitkaPluginBase):
    plugin_name = __file__

    def onGeneratedSourceCode(self, source_dir, onefile):
        if onefile:
            shutil.copyfile(
                BASE_DIR / "OnefileBootstrap.c",
                Path(source_dir) / "static_src" / "OnefileBootstrap.c",
            )
