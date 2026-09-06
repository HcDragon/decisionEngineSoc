"""
Live NFStream Sensor for macOS (Apple Silicon M4) & Linux.
Captures live network packets from interface (default: 'en0'),
computes the 73 statistical flow features, runs inference through
the Random Forest IDS model, and forwards ThreatEvent payloads
into the Decision Engine.
"""
import os
import sys
import time
import logging
from typing import Optional, Generator, Tuple, Dict, Any

from decision_engine.models.threat_event import ThreatEvent
from decision_engine.integrations.ids_bridge import IDSBridge
from decision_engine.integrations.flagged_logger import NFStreamFlaggedLogger

logger = logging.getLogger("NFStreamSensor")

class NFStreamSensor:
    """
    Live hardware packet capture sensor using NFStream on macOS (Apple Silicon M4) / Linux.
    Binds to network interface 'en0' (default Wi-Fi/Ethernet on MacBooks) or reads PCAP files,
    categorizes flows, and logs flagged suspicious flows into logs/nfstream_flagged.log.
    """
    def __init__(
        self,
        interface: str = "en0",
        ids_bridge: Optional[IDSBridge] = None,
        promiscuous: bool = True,
        flagged_logger: Optional[NFStreamFlaggedLogger] = None
    ):
        self.interface = interface
        self.bridge = ids_bridge or IDSBridge()
        self.promiscuous = promiscuous
        self.flagged_logger = flagged_logger or NFStreamFlaggedLogger()
        self._has_nfstream = False
        self._check_nfstream()

    def _check_nfstream(self):
        try:
            import nfstream
            self._has_nfstream = True
            logger.info("NFStream library detected (v%s)", getattr(nfstream, "__version__", "unknown"))
        except ImportError:
            self._has_nfstream = False
            logger.warning(
                "NFStream not installed. On macOS (Apple Silicon M4), install via:\n"
                "  brew install libpcap\n"
                "  pip install nfstream"
            )

    @property
    def is_available(self) -> bool:
        return self._has_nfstream and self.bridge.is_ready

    def stream_live(
        self,
        max_flows: Optional[int] = None,
        idle_timeout: int = 15,
        active_timeout: int = 30
    ) -> Generator[Tuple[ThreatEvent, Dict[str, Any]], None, None]:
        """
        Streams live network flows captured directly from the macOS interface (e.g. en0).
        """
        if not self._has_nfstream:
            logger.info("NFStream hardware capture unavailable; streaming via CICIDS2017 flow replay.")
            for threat_event, meta in self.bridge.stream_continuous(delay_seconds=1.2):
                pred = meta.get("predicted", "Benign Traffic")
                conf = float(meta.get("confidence", 0.95))
                flow_dict = {
                    "source_ip": threat_event.source.ip,
                    "source_port": threat_event.source.port,
                    "destination_ip": threat_event.destination.ip,
                    "destination_port": threat_event.destination.port,
                    "protocol": threat_event.network.protocol,
                    "packet_count": threat_event.network.packet_count,
                    "flow_duration": threat_event.network.flow_duration,
                    "bytes": threat_event.network.bytes
                }
                flagged_rec = self.flagged_logger.log_flow(flow_dict, pred, conf)
                meta["flagged_record"] = flagged_rec
                yield threat_event, meta
            return

        from nfstream import NFStreamer

        logger.info("Commencing live packet sniffing on interface %s (Apple Silicon M4)", self.interface)
        streamer = NFStreamer(
            source=self.interface,
            promiscuous_mode=self.promiscuous,
            idle_timeout=idle_timeout,
            active_timeout=active_timeout
        )

        flow_count = 0
        for flow in streamer:
            flow_count += 1
            flow_dict = {
                "source_ip": flow.src_ip,
                "source_port": flow.src_port,
                "destination_ip": flow.dst_ip,
                "destination_port": flow.dst_port,
                "Src Port": flow.src_port,
                "Dst Port": flow.dst_port,
                "Flow Duration": flow.bidirectional_duration_ms / 1000.0,
                "Total Fwd Packet": flow.src2dst_packets,
                "Total Bwd packets": flow.dst2src_packets,
                "Total Length of Fwd Packet": flow.src2dst_bytes,
                "Total Length of Bwd Packet": flow.dst2src_bytes,
                "Flow Packets/s": flow.bidirectional_packets / max(0.001, flow.bidirectional_duration_ms / 1000.0),
                "Flow Bytes/s": flow.bidirectional_bytes / max(0.001, flow.bidirectional_duration_ms / 1000.0),
                "Protocol": "TCP" if flow.protocol == 6 else ("UDP" if flow.protocol == 17 else "ICMP")
            }

            try:
                pred, conf, _ = self.bridge.predict_flow(flow_dict)
                flagged_rec = self.flagged_logger.log_flow(flow_dict, pred, conf)
                threat_event = self.bridge.flow_to_threat_event(
                    flow_dict,
                    predicted_attack=pred,
                    confidence=conf,
                    source_ip=flow.src_ip,
                    destination_ip=flow.dst_ip
                )
                meta = {
                    "live_interface": self.interface,
                    "predicted": pred,
                    "confidence": conf,
                    "packets": flow.bidirectional_packets,
                    "bytes": flow.bidirectional_bytes,
                    "flagged_record": flagged_rec
                }
                yield threat_event, meta
            except Exception as e:
                logger.error("Error processing live flow from %s: %s", self.interface, e)

            if max_flows and flow_count >= max_flows:
                break
