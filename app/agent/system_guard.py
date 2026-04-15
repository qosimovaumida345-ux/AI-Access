# ============================================================
# SHADOWFORGE OS — SYSTEM GUARD
# Pre-flight security check on ALL prompts.
# Detects attempts to access system files, credentials,
# or perform destructive operations.
# In sudo mode: logs but does NOT block.
# ============================================================

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.logger import get_logger

logger = get_logger("Agent.SystemGuard")


# ── THREAT LEVELS ─────────────────────────────────────────
class ThreatLevel(str, Enum):
    NONE     = "none"
    LOW      = "low"      # Suspicious but probably fine
    MEDIUM   = "medium"   # Needs user awareness
    HIGH     = "high"     # Potentially risky
    CRITICAL = "critical" # Block without sudo


# ── THREAT RESULT ─────────────────────────────────────────
@dataclass
class ThreatResult:
    level:       ThreatLevel
    is_critical: bool
    reason:      str
    matched_rules: List[str] = field(default_factory=list)
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_clean(self) -> bool:
        return self.level == ThreatLevel.NONE


# ── THREAT RULE ───────────────────────────────────────────
@dataclass
class ThreatRule:
    name:        str
    pattern:     re.Pattern
    level:       ThreatLevel
    reason:      str
    examples:    List[str] = field(default_factory=list)


# ── RULE DEFINITIONS ──────────────────────────────────────
def _build_rules() -> List[ThreatRule]:
    """Build all threat detection rules."""

    def rule(
        name: str, pattern: str, level: ThreatLevel, reason: str
    ) -> ThreatRule:
        return ThreatRule(
            name    = name,
            pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE),
            level   = level,
            reason  = reason,
        )

    return [

        # ── SYSTEM FILE ACCESS ────────────────────────────
        rule(
            "sys_etc",
            r'/etc/(passwd|shadow|sudoers|hosts|ssh)',
            ThreatLevel.CRITICAL,
            "Attempt to access system credential files",
        ),
        rule(
            "sys_ssh",
            r'(~|home)/[^/]+/\.ssh/(id_rsa|id_ed25519|known_hosts|authorized)',
            ThreatLevel.CRITICAL,
            "Attempt to access SSH private keys",
        ),
        rule(
            "sys_windows_system",
            r'C:\\Windows\\(System32|SysWOW64|drivers)',
            ThreatLevel.CRITICAL,
            "Attempt to access Windows system directory",
        ),
        rule(
            "sys_credentials",
            r'\.(aws|kube|gnupg|config/gcloud)/(credentials|token|key)',
            ThreatLevel.CRITICAL,
            "Attempt to access cloud credentials",
        ),
        rule(
            "sys_keychain",
            r'(Keychain|keychain|\.keystore)',
            ThreatLevel.HIGH,
            "Attempt to access system keychain/keystore",
        ),
        rule(
            "sys_registry",
            r'(HKEY_LOCAL_MACHINE|HKEY_CURRENT_USER|regedit)',
            ThreatLevel.HIGH,
            "Attempt to access Windows registry",
        ),

        # ── CREDENTIAL THEFT ──────────────────────────────
        rule(
            "steal_browser_cookies",
            r'(steal|grab|extract|dump|harvest).*(cookie|session|token)',
            ThreatLevel.CRITICAL,
            "Attempt to steal browser cookies or session tokens",
        ),
        rule(
            "keylogger",
            r'\b(keylog|keystroke.record|hook.*keyboard)',
            ThreatLevel.CRITICAL,
            "Keylogger pattern detected",
        ),
        rule(
            "screenshot_covert",
            r'\b(covert|hidden|silent|secret).*screenshot',
            ThreatLevel.HIGH,
            "Covert screenshot attempt detected",
        ),
        rule(
            "passwd_dump",
            r'\b(dump|extract|harvest).*(password|passwd|credential)',
            ThreatLevel.CRITICAL,
            "Password dumping attempt detected",
        ),

        # ── MALWARE PATTERNS ──────────────────────────────
        rule(
            "reverse_shell",
            r'(reverse.?shell|bind.?shell|nc.{0,10}-e|bash.{0,15}/dev/tcp)',
            ThreatLevel.CRITICAL,
            "Reverse shell pattern detected",
        ),
        rule(
            "ransomware",
            r'\b(encrypt.{0,20}files|ransomware|ransom.{0,10}demand)',
            ThreatLevel.CRITICAL,
            "Ransomware-related pattern detected",
        ),
        rule(
            "malware_dropper",
            r'(wget|curl).{0,30}(pipe|bash|sh|exec|eval)',
            ThreatLevel.HIGH,
            "Remote code execution dropper pattern",
        ),
        rule(
            "fork_bomb",
            r':\s*\(\s*\)\s*\{\s*:',  # :(){ :|:& };:
            ThreatLevel.CRITICAL,
            "Fork bomb pattern detected",
        ),
        rule(
            "rm_rf_root",
            r'rm\s+-[rf]+\s+(/\s*$|/\s+")',
            ThreatLevel.CRITICAL,
            "Attempt to delete root filesystem",
        ),

        # ── NETWORK SURVEILLANCE ──────────────────────────
        rule(
            "port_scan",
            r'\b(nmap|masscan|port.?scan|scan.{0,20}ports)',
            ThreatLevel.MEDIUM,
            "Network scanning tool usage",
        ),
        rule(
            "packet_sniff",
            r'\b(wireshark|tcpdump|packet.?sniff|intercept.{0,20}traffic)',
            ThreatLevel.MEDIUM,
            "Network packet capture attempt",
        ),
        rule(
            "arp_poison",
            r'\b(arp.?poison|arp.?spoof|man.in.the.middle)',
            ThreatLevel.HIGH,
            "ARP poisoning / MITM attack pattern",
        ),

        # ── SOCIAL ENGINEERING / PHISHING ─────────────────
        rule(
            "phishing_page",
            r'(fake.{0,20}login|phishing.{0,20}page|credential.{0,20}harvest)',
            ThreatLevel.HIGH,
            "Phishing page creation attempt",
        ),

        # ── CRYPTO MINING ─────────────────────────────────
        rule(
            "crypto_miner",
            r'\b(cryptominer|monero|xmrig|coinhive|mine.{0,10}crypto)',
            ThreatLevel.HIGH,
            "Cryptocurrency miner pattern detected",
        ),

        # ── SELF-REPLICATION ──────────────────────────────
        rule(
            "worm_spread",
            r'\b(spread.{0,20}network|infect.{0,20}(host|machine|device)|self.replic)',
            ThreatLevel.HIGH,
            "Self-replicating/worm behavior pattern",
        ),

        # ── DATA EXFILTRATION ─────────────────────────────
        rule(
            "data_exfil",
            r'\b(exfiltrat|data.theft|steal.{0,20}data|send.{0,30}(to|external))',
            ThreatLevel.MEDIUM,
            "Potential data exfiltration pattern",
        ),

        # ── PRIVILEGE ESCALATION ──────────────────────────
        rule(
            "priv_esc",
            r'\b(privilege.escal|root.exploit|setuid|suid.exploit)',
            ThreatLevel.HIGH,
            "Privilege escalation attempt",
        ),

        # ── LOW LEVEL WARNINGS ────────────────────────────
        rule(
            "disk_wipe",
            r'\b(dd.{0,20}if=/dev/zero|shred.{0,20}/dev|wipe.{0,20}disk)',
            ThreatLevel.CRITICAL,
            "Disk wiping operation detected",
        ),
        rule(
            "boot_sector",
            r'\b(boot.?sector|mbr|master.?boot.?record)',
            ThreatLevel.HIGH,
            "Boot sector modification attempt",
        ),
    ]


# Pre-compile all rules once at module load
THREAT_RULES: List[ThreatRule] = _build_rules()

# Patterns that are always safe (override medium/high)
SAFE_CONTEXT_PATTERNS = [
    r'\b(explain|understand|learn|tutorial|how.does|what.is)\b',
    r'\b(study|academic|research|educational)\b',
    r'\b(detect|prevent|defend|protect|security.audit)\b',
    r'\b(pen.test|penetration.test|ethical.hack|ctf)\b',
]


# ── MAIN GUARD CLASS ──────────────────────────────────────
class SystemGuard:
    """
    Pre-flight security scanner for all user prompts.

    In normal mode: blocks CRITICAL threats.
    In sudo mode: logs threats but does not block.
    Keeps an audit trail of all checks.
    """

    def __init__(self):
        self._rules     = THREAT_RULES
        self._audit: List[Dict] = []
        self._blocked_count = 0
        self._checked_count = 0

        logger.info(
            f"SystemGuard initialized with {len(self._rules)} threat rules."
        )

    # ── SAFE CONTEXT CHECK ────────────────────────────────
    def _has_safe_context(self, text: str) -> bool:
        """Check if the prompt has educational/defensive context."""
        for pattern in SAFE_CONTEXT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    # ── MAIN CHECK ────────────────────────────────────────
    def check_prompt(self, prompt: str) -> ThreatResult:
        """
        Scan a prompt for security threats.
        Returns ThreatResult.
        """
        self._checked_count += 1

        if not prompt or not prompt.strip():
            return ThreatResult(
                level       = ThreatLevel.NONE,
                is_critical = False,
                reason      = "Empty prompt",
            )

        # Check for safe educational context
        is_educational = self._has_safe_context(prompt)

        matched: List[ThreatRule] = []
        highest_level = ThreatLevel.NONE

        for rule in self._rules:
            if rule.pattern.search(prompt):
                matched.append(rule)

                # Educational context reduces HIGH → MEDIUM
                effective_level = rule.level
                if is_educational and rule.level == ThreatLevel.HIGH:
                    effective_level = ThreatLevel.MEDIUM
                    logger.debug(
                        f"Rule '{rule.name}' reduced from HIGH to MEDIUM "
                        f"(educational context)"
                    )

                # Track highest threat level
                level_order = [
                    ThreatLevel.NONE, ThreatLevel.LOW,
                    ThreatLevel.MEDIUM, ThreatLevel.HIGH,
                    ThreatLevel.CRITICAL
                ]
                if level_order.index(effective_level) > \
                   level_order.index(highest_level):
                    highest_level = effective_level

        # Build result
        if not matched:
            result = ThreatResult(
                level       = ThreatLevel.NONE,
                is_critical = False,
                reason      = "No threats detected",
            )
        else:
            matched_names  = [r.name for r in matched]
            primary_reason = matched[0].reason if matched else "Unknown threat"

            is_critical = highest_level == ThreatLevel.CRITICAL

            if is_critical:
                self._blocked_count += 1

            result = ThreatResult(
                level          = highest_level,
                is_critical    = is_critical,
                reason         = primary_reason,
                matched_rules  = matched_names,
            )

            log_level = logging.CRITICAL if is_critical else (
                logging.WARNING if highest_level in (ThreatLevel.HIGH,) else
                logging.INFO
            )

            logger.log(
                log_level,
                f"Threat detected: level={highest_level.value} "
                f"rules={matched_names} "
                f"educational={is_educational}"
            )

        # Audit
        self._audit.append({
            "ts":       datetime.now().isoformat(),
            "prompt":   prompt[:100],
            "level":    result.level.value,
            "critical": result.is_critical,
            "rules":    result.matched_rules,
        })

        # Trim audit
        if len(self._audit) > 5000:
            self._audit = self._audit[-2500:]

        return result

    # ── BULK CHECK ────────────────────────────────────────
    def check_code(self, code: str, language: str = "") -> ThreatResult:
        """
        Check generated code for dangerous patterns.
        Slightly different rules for code vs prompts.
        """
        # For code, we care more about actual dangerous operations
        code_specific_patterns = [
            (re.compile(r'os\.system\([\'"]rm\s+-rf'), ThreatLevel.CRITICAL, "rm -rf in os.system"),
            (re.compile(r'subprocess.*rm.*-rf', re.I), ThreatLevel.CRITICAL, "rm -rf in subprocess"),
            (re.compile(r'shutil\.rmtree\(["\']\/'), ThreatLevel.HIGH, "rmtree on root path"),
            (re.compile(r'open\(["\']\/etc\/(passwd|shadow)'), ThreatLevel.CRITICAL, "Opening /etc/passwd"),
            (re.compile(r'eval\(.*input\(', re.I), ThreatLevel.HIGH, "eval(input()) pattern"),
            (re.compile(r'exec\(.*input\(', re.I), ThreatLevel.HIGH, "exec(input()) pattern"),
            (re.compile(r'pickle\.loads\(.*request', re.I), ThreatLevel.HIGH, "Unsafe pickle deserialization"),
            (re.compile(r'__import__\([\'"]os[\'"]', re.I), ThreatLevel.MEDIUM, "Hidden os import"),
        ]

        matched_names = []
        highest_level = ThreatLevel.NONE
        level_order = [
            ThreatLevel.NONE, ThreatLevel.LOW,
            ThreatLevel.MEDIUM, ThreatLevel.HIGH,
            ThreatLevel.CRITICAL
        ]

        for pattern, level, name in code_specific_patterns:
            if pattern.search(code):
                matched_names.append(name)
                if level_order.index(level) > level_order.index(highest_level):
                    highest_level = level

        # Also run regular prompt check
        prompt_result = self.check_prompt(code[:2000])
        if level_order.index(prompt_result.level) > level_order.index(highest_level):
            highest_level = prompt_result.level
            matched_names.extend(prompt_result.matched_rules)

        if not matched_names:
            return ThreatResult(
                level       = ThreatLevel.NONE,
                is_critical = False,
                reason      = "Code appears safe",
            )

        return ThreatResult(
            level          = highest_level,
            is_critical    = highest_level == ThreatLevel.CRITICAL,
            reason         = matched_names[0] if matched_names else "Unknown",
            matched_rules  = matched_names,
        )

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> Dict:
        return {
            "total_checked":  self._checked_count,
            "total_blocked":  self._blocked_count,
            "rule_count":     len(self._rules),
            "audit_entries":  len(self._audit),
            "block_rate":     (
                f"{self._blocked_count/self._checked_count*100:.1f}%"
                if self._checked_count > 0 else "0%"
            ),
        }

    def get_recent_threats(self, n: int = 20) -> List[Dict]:
        threats = [e for e in self._audit if e["level"] != "none"]
        return threats[-n:]

    def clear_audit(self) -> None:
        self._audit.clear()
        logger.info("SystemGuard audit cleared.")

    def __repr__(self) -> str:
        return (
            f"SystemGuard(rules={len(self._rules)}, "
            f"checked={self._checked_count}, "
            f"blocked={self._blocked_count})"
        )