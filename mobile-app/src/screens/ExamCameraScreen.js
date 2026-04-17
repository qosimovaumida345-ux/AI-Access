import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Dimensions, StatusBar, ActivityIndicator
} from 'react-native';
import { X, ScanSearch, ShieldAlert, Cpu, ChevronDown } from 'lucide-react-native';

const { width, height } = Dimensions.get('window');

const COLORS = {
  void:     '#040209',
  surface2: 'rgba(22, 10, 48, 0.96)',
  red600:   '#dc2626',
  red400:   '#f87171',
  red300:   '#fca5a5',
  violet400:'#a78bfa',
  violet500:'#8b5cf6',
  cyan400:  '#22d3ee',
  textPri:  '#f1efff',
  textSec:  '#b3a8d4',
  textMuted:'#6b5f8a',
};

export default function ExamCameraScreen({ token, onClose }) {
  const [answer, setAnswer]     = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanDone, setScanDone] = useState(false);

  const captureAndAnalyze = () => {
    if (scanning) return;
    setAnswer('');
    setScanDone(false);
    setScanning(true);
    // Simulated: replace with actual expo-camera capture + API call
    setTimeout(() => {
      setScanning(false);
      setScanDone(true);
      setAnswer('The answer to the question is: Mitochondria (Option B)');
    }, 2000);
  };

  const reset = () => {
    setAnswer('');
    setScanDone(false);
  };

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="#000" />

      {/* ── CAMERA VIEWFINDER ────────────────────────────── */}
      <View style={styles.viewfinder}>
        {/* Corner brackets */}
        {[
          { top: 32, left: 32, borderTopWidth: 2, borderLeftWidth: 2 },
          { top: 32, right: 32, borderTopWidth: 2, borderRightWidth: 2 },
          { bottom: 32, left: 32, borderBottomWidth: 2, borderLeftWidth: 2 },
          { bottom: 32, right: 32, borderBottomWidth: 2, borderRightWidth: 2 },
        ].map((s, i) => (
          <View key={i} style={[styles.corner, s, { borderColor: COLORS.red400 }]} />
        ))}

        {/* Scan line */}
        {scanning && (
          <View style={styles.scanLine}>
            <View style={styles.scanLineInner} />
          </View>
        )}

        <Cpu size={28} color="rgba(248,113,113,0.25)" strokeWidth={1} />
        <Text style={styles.viewfinderLabel}>CAMERA VIEWFINDER</Text>
        <Text style={styles.viewfinderHint}>Point at the screen or paper</Text>
      </View>

      {/* ── TOP BAR ──────────────────────────────────────── */}
      <View style={styles.topBar}>
        <View style={styles.topBadge}>
          <ShieldAlert size={12} color={COLORS.red400} strokeWidth={2} />
          <Text style={styles.topBadgeText}>EXAM MODE</Text>
        </View>
        <TouchableOpacity style={styles.closeBtn} onPress={onClose} activeOpacity={0.8}>
          <X size={16} color={COLORS.textSec} strokeWidth={2} />
        </TouchableOpacity>
      </View>

      {/* ── ANSWER OVERLAY ───────────────────────────────── */}
      {(scanDone && answer) && (
        <View style={styles.answerOverlay} pointerEvents="none">
          <View style={styles.answerCard}>
            <View style={styles.answerHeader}>
              <View style={styles.answerDot} />
              <Text style={styles.answerHeaderText}>AI ANALYSIS</Text>
              <View style={{ flex: 1 }} />
              <ChevronDown size={12} color={COLORS.red400} />
            </View>
            <Text style={styles.answerText}>{answer}</Text>
          </View>
        </View>
      )}

      {/* ── CONTROLS ─────────────────────────────────────── */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.deactivateBtn} onPress={onClose} activeOpacity={0.85}>
          <X size={15} color={COLORS.red400} strokeWidth={2} />
          <Text style={styles.deactivateText}>Deactivate</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.captureBtn, scanning && styles.captureBtnDisabled]}
          onPress={captureAndAnalyze}
          activeOpacity={0.85}
          disabled={scanning}
        >
          {scanning ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <ScanSearch size={18} color="#fff" strokeWidth={1.8} />
          )}
          <Text style={styles.captureText}>
            {scanning ? 'Scanning...' : 'Parse Screen'}
          </Text>
        </TouchableOpacity>

        {scanDone && (
          <TouchableOpacity style={styles.resetBtn} onPress={reset} activeOpacity={0.8}>
            <Text style={styles.resetText}>Clear</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* ── BOTTOM HINT ──────────────────────────────────── */}
      <Text style={styles.bottomHint}>
        Token: {token} · Neural link active
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#000',
    position: 'relative',
  },

  // Viewfinder
  viewfinder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 24,
    height: 24,
  },
  scanLine: {
    position: 'absolute',
    top: '20%',
    left: '10%',
    right: '10%',
    height: 1,
    overflow: 'hidden',
  },
  scanLineInner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: COLORS.red400,
    shadowColor: COLORS.red400,
    shadowOpacity: 1,
    shadowRadius: 6,
  },
  viewfinderLabel: {
    fontWeight: '700',
    fontSize: 11,
    color: 'rgba(248,113,113,0.3)',
    letterSpacing: 2.5,
    marginTop: 12,
  },
  viewfinderHint: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.25)',
    letterSpacing: 0.3,
  },

  // Top bar
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingTop: 52,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  topBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(220,38,38,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(248,113,113,0.25)',
  },
  topBadgeText: {
    fontWeight: '700',
    fontSize: 10,
    color: COLORS.red400,
    letterSpacing: 1.5,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Answer overlay
  answerOverlay: {
    position: 'absolute',
    top: 120,
    left: 20,
    right: 20,
    zIndex: 999,
  },
  answerCard: {
    backgroundColor: 'rgba(0,0,0,0.88)',
    borderWidth: 1,
    borderColor: 'rgba(248,113,113,0.35)',
    borderRadius: 14,
    padding: 16,
    shadowColor: COLORS.red400,
    shadowOpacity: 0.4,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 0 },
    elevation: 12,
  },
  answerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    marginBottom: 10,
  },
  answerDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: COLORS.red400,
    shadowColor: COLORS.red400,
    shadowOpacity: 1,
    shadowRadius: 4,
  },
  answerHeaderText: {
    fontWeight: '700',
    fontSize: 10,
    color: COLORS.red400,
    letterSpacing: 1.5,
  },
  answerText: {
    fontWeight: '600',
    fontSize: 16,
    color: '#fff',
    lineHeight: 24,
  },

  // Controls
  controls: {
    position: 'absolute',
    bottom: 48,
    left: 20,
    right: 20,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  deactivateBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderRadius: 30,
    backgroundColor: 'rgba(220,38,38,0.10)',
    borderWidth: 1,
    borderColor: 'rgba(248,113,113,0.28)',
  },
  deactivateText: {
    color: COLORS.red400,
    fontWeight: '600',
    fontSize: 13,
  },
  captureBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 22,
    paddingVertical: 14,
    borderRadius: 30,
    backgroundColor: COLORS.red600,
    shadowColor: COLORS.red600,
    shadowOpacity: 0.5,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 3 },
    elevation: 8,
  },
  captureBtnDisabled: {
    backgroundColor: 'rgba(220,38,38,0.4)',
    shadowOpacity: 0,
    elevation: 0,
  },
  captureText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  resetBtn: {
    paddingHorizontal: 14,
    paddingVertical: 14,
    borderRadius: 30,
    backgroundColor: 'rgba(255,255,255,0.07)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
  },
  resetText: {
    color: 'rgba(255,255,255,0.5)',
    fontSize: 13,
    fontWeight: '500',
  },

  bottomHint: {
    position: 'absolute',
    bottom: 16,
    left: 0,
    right: 0,
    textAlign: 'center',
    fontSize: 10,
    color: 'rgba(255,255,255,0.15)',
    letterSpacing: 0.4,
  },
});
