import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ScrollView, Dimensions, StatusBar
} from 'react-native';
import {
  Fingerprint, MessageSquare, FolderOpen,
  Globe, ShieldAlert, Zap, Activity, ChevronRight
} from 'lucide-react-native';

const { width } = Dimensions.get('window');

const COLORS = {
  void:      '#040209',
  deep:      '#0c0520',
  surface:   'rgba(22, 10, 48, 0.90)',
  surface2:  'rgba(32, 16, 64, 0.92)',
  violet700: '#5b21b6',
  violet500: '#8b5cf6',
  violet400: '#a78bfa',
  violet300: '#c4b5fd',
  cyan400:   '#22d3ee',
  cyan300:   '#67e8f9',
  red400:    '#f87171',
  red600:    '#dc2626',
  green500:  '#10b981',
  textPri:   '#f1efff',
  textSec:   '#b3a8d4',
  textMuted: '#6b5f8a',
  borderDef: 'rgba(139, 92, 246, 0.20)',
  borderStr: 'rgba(139, 92, 246, 0.45)',
};

// ── GRID CARD ──────────────────────────────────────────────
function GridCard({ icon: Icon, label, color = COLORS.violet400, onPress }) {
  const [pressed, setPressed] = useState(false);
  return (
    <TouchableOpacity
      style={[styles.gridCard, pressed && styles.gridCardPressed]}
      onPressIn={() => setPressed(true)}
      onPressOut={() => setPressed(false)}
      onPress={onPress}
      activeOpacity={1}
    >
      <View style={[styles.gridIconWrap, { borderColor: color + '33', backgroundColor: color + '15' }]}>
        <Icon size={22} color={color} strokeWidth={1.5} />
      </View>
      <Text style={styles.gridLabel}>{label}</Text>
      <ChevronRight size={14} color={COLORS.textMuted} style={{ marginTop: 2 }} />
    </TouchableOpacity>
  );
}

// ── BIND SCREEN ────────────────────────────────────────────
function BindScreen({ onBind }) {
  const [val, setVal] = useState('');
  const [focused, setFocused] = useState(false);

  return (
    <View style={styles.bindRoot}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.void} />

      {/* Ambient glow */}
      <View style={styles.ambientGlow} />

      <View style={styles.bindCard}>
        {/* Icon */}
        <View style={styles.bindIconRing}>
          <View style={styles.bindIconInner}>
            <Fingerprint size={32} color={COLORS.violet400} strokeWidth={1.5} />
          </View>
        </View>

        <Text style={styles.bindTitle}>System Bind Required</Text>
        <Text style={styles.bindSubtitle}>
          Enter the Device Sync Token generated from your Config Website.
        </Text>

        <View style={[styles.inputWrap, focused && styles.inputWrapFocused]}>
          <Zap size={14} color={focused ? COLORS.violet400 : COLORS.textMuted} style={{ marginRight: 10 }} />
          <TextInput
            style={styles.input}
            placeholder="e.g. AI-9XXXXX"
            placeholderTextColor={COLORS.textMuted}
            value={val}
            onChangeText={setVal}
            autoCapitalize="characters"
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            selectionColor={COLORS.violet400}
          />
        </View>

        <TouchableOpacity
          style={[styles.bindBtn, !val.trim() && styles.bindBtnDisabled]}
          onPress={() => val.trim() && onBind(val)}
          activeOpacity={0.8}
        >
          <Zap size={16} color="#fff" strokeWidth={2} />
          <Text style={styles.bindBtnText}>Establish Uplink</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.bindFooter}>ShadowForge OS · Secure Neural Channel</Text>
    </View>
  );
}

// ── MAIN SCREEN ────────────────────────────────────────────
export default function HomeScreen({ token, onBind, onToggleExam }) {
  if (!token || token === 'NOT_BOUND') return <BindScreen onBind={onBind} />;

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      <StatusBar barStyle="light-content" backgroundColor={COLORS.void} />

      {/* Status bar */}
      <View style={styles.statusCard}>
        <View style={styles.statusRow}>
          <View style={styles.statusDot} />
          <Text style={styles.statusLabel}>STATUS: OPERATIONAL</Text>
          <View style={{ flex: 1 }} />
          <Activity size={14} color={COLORS.green500} strokeWidth={1.5} />
        </View>
        <View style={styles.divider} />
        <Text style={styles.tokenText} numberOfLines={1}>
          UPLINK: {token}
        </Text>
      </View>

      {/* Grid */}
      <Text style={styles.sectionLabel}>Agent Interfaces</Text>
      <View style={styles.grid}>
        <GridCard icon={MessageSquare} label="Chat Client"  color={COLORS.violet400} />
        <GridCard icon={FolderOpen}    label="Files"        color={COLORS.cyan400}   />
        <GridCard icon={Globe}         label="Web Actions"  color={COLORS.violet300} />
        <GridCard icon={Zap}           label="Terminal"     color={COLORS.cyan300}   />
      </View>

      {/* Exam mode card */}
      <Text style={styles.sectionLabel}>Exam Mode</Text>
      <TouchableOpacity style={styles.examCard} onPress={onToggleExam} activeOpacity={0.85}>
        <View style={styles.examHeader}>
          <View style={styles.examIconWrap}>
            <ShieldAlert size={20} color={COLORS.red400} strokeWidth={1.5} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.examTitle}>Activate Exam Mode</Text>
            <Text style={styles.examBadge}>AI VISION ACTIVE</Text>
          </View>
          <ChevronRight size={18} color={COLORS.red400} />
        </View>
        <Text style={styles.examDesc}>
          Grants AI access to device camera for real-time visual buffering.
          Displays minimal overlay for analysis results.
        </Text>
        <View style={styles.examDivider} />
        <View style={styles.examFooter}>
          <View style={styles.examDot} />
          <Text style={styles.examFooterText}>Tap to enable · Minimal red overlay</Text>
        </View>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ── STYLES ────────────────────────────────────────────────
const styles = StyleSheet.create({
  // Bind screen
  bindRoot: {
    flex: 1,
    backgroundColor: COLORS.void,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  ambientGlow: {
    position: 'absolute',
    top: '-10%',
    width: '80%',
    height: '40%',
    backgroundColor: 'transparent',
    borderRadius: 999,
    shadowColor: COLORS.violet700,
    shadowOpacity: 0.35,
    shadowRadius: 80,
    shadowOffset: { width: 0, height: 0 },
    elevation: 0,
  },
  bindCard: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: COLORS.surface2,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.5,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 12,
  },
  bindIconRing: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    backgroundColor: 'rgba(91, 33, 182, 0.08)',
  },
  bindIconInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: COLORS.borderStr,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(139, 92, 246, 0.12)',
  },
  bindTitle: {
    fontWeight: '700',
    fontSize: 20,
    color: COLORS.textPri,
    textAlign: 'center',
    letterSpacing: -0.3,
  },
  bindSubtitle: {
    fontSize: 13,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: 10,
    lineHeight: 20,
    paddingHorizontal: 8,
  },
  inputWrap: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.4)',
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    borderRadius: 12,
    padding: 14,
    marginTop: 28,
    marginBottom: 16,
    transition: 'border-color 0.2s',
  },
  inputWrapFocused: {
    borderColor: COLORS.violet500,
  },
  input: {
    flex: 1,
    color: COLORS.textPri,
    fontSize: 15,
    fontWeight: '500',
    letterSpacing: 1,
  },
  bindBtn: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: COLORS.violet700,
    borderRadius: 12,
    paddingVertical: 15,
    shadowColor: COLORS.violet700,
    shadowOpacity: 0.45,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  bindBtnDisabled: {
    backgroundColor: 'rgba(91,33,182,0.35)',
    shadowOpacity: 0,
    elevation: 0,
  },
  bindBtnText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 15,
    letterSpacing: 0.3,
  },
  bindFooter: {
    marginTop: 32,
    fontSize: 11,
    color: COLORS.textMuted,
    letterSpacing: 0.5,
  },

  // Home screen
  root: {
    flex: 1,
    backgroundColor: COLORS.void,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  statusCard: {
    backgroundColor: COLORS.surface2,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    padding: 16,
    marginBottom: 28,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: COLORS.green500,
    shadowColor: COLORS.green500,
    shadowOpacity: 0.8,
    shadowRadius: 4,
  },
  statusLabel: {
    fontWeight: '700',
    fontSize: 11,
    color: COLORS.green500,
    letterSpacing: 1.5,
  },
  divider: {
    height: 1,
    backgroundColor: COLORS.borderDef,
    marginVertical: 10,
  },
  tokenText: {
    fontSize: 11,
    color: COLORS.textMuted,
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },

  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    marginBottom: 14,
  },

  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 28,
  },
  gridCard: {
    width: (width - 52) / 2,
    backgroundColor: COLORS.surface2,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: COLORS.borderDef,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  gridCardPressed: {
    borderColor: COLORS.borderStr,
    backgroundColor: 'rgba(91,33,182,0.15)',
  },
  gridIconWrap: {
    width: 38,
    height: 38,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  gridLabel: {
    flex: 1,
    color: COLORS.textSec,
    fontSize: 13,
    fontWeight: '500',
  },

  examCard: {
    backgroundColor: 'rgba(220, 38, 38, 0.05)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(220, 38, 38, 0.22)',
    padding: 20,
  },
  examHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  examIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 11,
    backgroundColor: 'rgba(220,38,38,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(220,38,38,0.30)',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  examTitle: {
    color: COLORS.red400,
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: -0.2,
  },
  examBadge: {
    fontSize: 10,
    color: 'rgba(248,113,113,0.6)',
    fontWeight: '600',
    letterSpacing: 1.2,
    marginTop: 2,
  },
  examDesc: {
    color: COLORS.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  examDivider: {
    height: 1,
    backgroundColor: 'rgba(220,38,38,0.12)',
    marginVertical: 14,
  },
  examFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  examDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: COLORS.red400,
    shadowColor: COLORS.red400,
    shadowOpacity: 0.8,
    shadowRadius: 3,
  },
  examFooterText: {
    fontSize: 11,
    color: 'rgba(248,113,113,0.6)',
    letterSpacing: 0.3,
  },
});
