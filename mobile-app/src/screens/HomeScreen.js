import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { ShieldAlert, Fingerprint } from 'lucide-react-native';

export default function HomeScreen({ token, onBind, onToggleExam }) {
  const [inputToken, setInputToken] = useState('');

  if (!token) {
    return (
      <View style={styles.centerContainer}>
        <Fingerprint size={64} color="#3b82f6" />
        <Text style={styles.title}>System Bind Required</Text>
        <Text style={styles.subtitle}>Enter the exact Device Sync Token generated manually from your Config Website.</Text>
        
        <TextInput
          style={styles.input}
          placeholder="e.g. AI-9XXXXX"
          placeholderTextColor="#64748b"
          value={inputToken}
          onChangeText={setInputToken}
          autoCapitalize="characters"
        />
        
        <TouchableOpacity style={styles.button} onPress={() => onBind(inputToken)}>
          <Text style={styles.buttonText}>Establish Uplink</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 20 }}>
      <View style={styles.headerBox}>
        <Text style={styles.statusText}>STATUS: OPERATIONAL</Text>
        <Text style={styles.tokenText}>TOKEN: {token}</Text>
      </View>

      <Text style={styles.sectionTitle}>Agent Interfaces</Text>
      
      <View style={styles.grid}>
        <TouchableOpacity style={styles.gridItem}>
          <Text style={styles.gridIcon}>💬</Text>
          <Text style={styles.gridText}>Chat Client</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.gridItem}>
          <Text style={styles.gridIcon}>📁</Text>
          <Text style={styles.gridText}>Files & Assets</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.gridItem}>
          <Text style={styles.gridIcon}>🌐</Text>
          <Text style={styles.gridText}>Web Actions</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity style={styles.examCard} onPress={onToggleExam}>
        <ShieldAlert size={32} color="#f87171" style={{ marginBottom: 10 }} />
        <Text style={styles.examTitle}>Activate Exam Mode</Text>
        <Text style={styles.examDesc}>
          Grants AI access to device camera for real-time visual buffering.
          Will show minimal, red-colored overlay for analysis results.
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 20 },
  subtitle: { color: '#94a3b8', textAlign: 'center', marginVertical: 10 },
  input: {
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.1)',
    color: '#fff',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 10,
    padding: 15,
    marginTop: 20,
    shadowColor: '#3b82f6',
    shadowOpacity: 0.2,
    shadowRadius: 10,
  },
  button: {
    width: '100%',
    backgroundColor: '#3b82f6',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
  },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  headerBox: {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    padding: 20,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)',
    marginBottom: 30,
  },
  statusText: { color: '#3b82f6', fontWeight: '900', letterSpacing: 2 },
  tokenText: { color: '#e2e8f0', marginTop: 5, fontFamily: 'monospace' },
  sectionTitle: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 15 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  gridItem: {
    width: '48%',
    backgroundColor: '#1e293b',
    padding: 20,
    borderRadius: 15,
    marginBottom: 15,
    alignItems: 'center'
  },
  gridIcon: { fontSize: 32, marginBottom: 10 },
  gridText: { color: '#cbd5e1', fontWeight: '600' },
  examCard: {
    backgroundColor: 'rgba(248, 113, 113, 0.1)',
    padding: 20,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(248, 113, 113, 0.3)',
    marginTop: 20,
  },
  examTitle: { color: '#f87171', fontSize: 18, fontWeight: 'bold', marginBottom: 5 },
  examDesc: { color: '#fca5a5', opacity: 0.8, lineHeight: 20 },
});
