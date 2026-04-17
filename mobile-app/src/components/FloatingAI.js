import React, { useRef, useState } from 'react';
import {
  View, Text, StyleSheet, Animated,
  PanResponder, TouchableOpacity, Dimensions
} from 'react-native';
import { Bot, X, Mic, MicOff, Zap } from 'lucide-react-native';

const COLORS = {
  void:      '#040209',
  surface2:  'rgba(22, 10, 48, 0.97)',
  violet700: '#5b21b6',
  violet500: '#8b5cf6',
  violet400: '#a78bfa',
  cyan400:   '#22d3ee',
  red400:    '#f87171',
  textPri:   '#f1efff',
  textSec:   '#b3a8d4',
  textMuted: '#6b5f8a',
  borderDef: 'rgba(139, 92, 246, 0.22)',
  borderStr: 'rgba(139, 92, 246, 0.50)',
};

const { width: SW, height: SH } = Dimensions.get('window');

export default function FloatingAI() {
  const pan      = useRef(new Animated.ValueXY()).current;
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const [expanded, setExpanded]   = useState(false);
  const [listening, setListening] = useState(false);

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) =>
        !expanded && (Math.abs(g.dx) > 4 || Math.abs(g.dy) > 4),
      onPanResponderGrant: () => {
        pan.setOffset({ x: pan.x._value, y: pan.y._value });
        Animated.spring(scaleAnim, { toValue: 0.9, useNativeDriver: true }).start();
      },
      onPanResponderMove: Animated.event(
        [null, { dx: pan.x, dy: pan.y }],
        { useNativeDriver: false }
      ),
      onPanResponderRelease: () => {
        pan.flattenOffset();
        Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true, tension: 200 }).start();
      },
    })
  ).current;

  const openPanel = () => {
    setExpanded(true);
    Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true }).start();
  };

  const closePanel = () => {
    setExpanded(false);
    setListening(false);
  };

  const toggleMic = () => setListening(l => !l);

  return (
    <Animated.View
      style={[
        styles.container,
        { transform: [{ translateX: pan.x }, { translateY: pan.y }, { scale: scaleAnim }] },
      ]}
      {...(!expanded ? panResponder.panHandlers : {})}
    >
      {/* ── COLLAPSED BUTTON ─────────────────────────────── */}
      {!expanded && (
        <TouchableOpacity
          style={styles.fab}
          onPress={openPanel}
          activeOpacity={0.85}
        >
          {/* Outer ring */}
          <Animated.View style={styles.fabRing} />
          <Bot size={22} color="#fff" strokeWidth={1.8} />
        </TouchableOpacity>
      )}

      {/* ── EXPANDED PANEL ───────────────────────────────── */}
      {expanded && (
        <View style={styles.panel}>
          {/* Header */}
          <View style={styles.panelHeader}>
            <View style={styles.panelTitleRow}>
              <View style={styles.panelDot} />
              <Text style={styles.panelTitle}>AI Assistant</Text>
            </View>
            <TouchableOpacity
              style={styles.closeBtn}
              onPress={closePanel}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <X size={15} color={COLORS.textMuted} strokeWidth={2} />
            </TouchableOpacity>
          </View>

          {/* Divider */}
          <View style={styles.panelDivider} />

          {/* Status */}
          <Text style={styles.panelStatus}>
            {listening ? 'Listening for voice input...' : 'Tap microphone to start'}
          </Text>

          {/* Mic button */}
          <TouchableOpacity
            style={[styles.micBtn, listening && styles.micBtnActive]}
            onPress={toggleMic}
            activeOpacity={0.8}
          >
            <View style={[styles.micInner, listening && styles.micInnerActive]}>
              {listening
                ? <MicOff size={22} color={COLORS.red400} strokeWidth={1.8} />
                : <Mic    size={22} color={COLORS.violet400} strokeWidth={1.8} />
              }
            </View>
            {listening && <View style={styles.micPulse} />}
          </TouchableOpacity>

          {/* Footer hint */}
          <View style={styles.panelFooter}>
            <Zap size={10} color={COLORS.textMuted} />
            <Text style={styles.panelFooterText}>ShadowForge Neural Link</Text>
          </View>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 110,
    right: 20,
    zIndex: 9999,
  },

  // FAB
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.violet700,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.violet700,
    shadowOpacity: 0.55,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 4 },
    elevation: 10,
    borderWidth: 1,
    borderColor: COLORS.borderStr,
  },
  fabRing: {
    position: 'absolute',
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 1,
    borderColor: 'rgba(91,33,182,0.3)',
  },

  // Panel
  panel: {
    width: 240,
    backgroundColor: COLORS.surface2,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: COLORS.borderStr,
    padding: 18,
    shadowColor: '#000',
    shadowOpacity: 0.55,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 14,
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  panelTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  panelDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: COLORS.violet400,
    shadowColor: COLORS.violet400,
    shadowOpacity: 0.9,
    shadowRadius: 4,
  },
  panelTitle: {
    color: COLORS.textPri,
    fontWeight: '600',
    fontSize: 14,
    letterSpacing: -0.2,
  },
  closeBtn: {
    width: 28,
    height: 28,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    alignItems: 'center',
    justifyContent: 'center',
  },
  panelDivider: {
    height: 1,
    backgroundColor: COLORS.borderDef,
    marginBottom: 16,
  },
  panelStatus: {
    fontSize: 11,
    color: COLORS.textMuted,
    textAlign: 'center',
    letterSpacing: 0.2,
    marginBottom: 18,
  },

  // Mic
  micBtn: {
    alignSelf: 'center',
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(139,92,246,0.08)',
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    marginBottom: 16,
    position: 'relative',
  },
  micBtnActive: {
    backgroundColor: 'rgba(220,38,38,0.08)',
    borderColor: 'rgba(248,113,113,0.35)',
  },
  micInner: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(91,33,182,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(139,92,246,0.30)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  micInnerActive: {
    backgroundColor: 'rgba(220,38,38,0.12)',
    borderColor: 'rgba(248,113,113,0.40)',
  },
  micPulse: {
    position: 'absolute',
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1,
    borderColor: 'rgba(248,113,113,0.2)',
  },

  // Footer
  panelFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
  },
  panelFooterText: {
    fontSize: 10,
    color: COLORS.textMuted,
    letterSpacing: 0.5,
  },
});
