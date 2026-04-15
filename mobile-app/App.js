import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  View, 
  Text, 
  SafeAreaView, 
  StatusBar, 
  Modal, 
  TextInput, 
  TouchableOpacity,
  ActivityIndicator,
  Animated,
  Easing
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Settings as SettingsIcon, Zap, Globe, Key, X } from 'lucide-react-native';
import HomeScreen from './src/screens/HomeScreen';
import FloatingAI from './src/components/FloatingAI';
import ExamCameraScreen from './src/screens/ExamCameraScreen';
import { initSocket, checkHealth } from './src/utils/api';

export default function App() {
  const [token, setToken] = useState(null);
  const [examMode, setExamMode] = useState(false);
  const [isBooting, setIsBooting] = useState(true);
  const [bootMessage, setBootMessage] = useState('Initializing Kernal...');
  const [showSettings, setShowSettings] = useState(false);
  
  // Settings States
  const [backendUrl, setBackendUrl] = useState('');
  const [apiKeys, setApiKeys] = useState({});

  useEffect(() => {
    const loadConfig = async () => {
      const storedToken = await AsyncStorage.getItem('DEVICE_TOKEN');
      const storedUrl = await AsyncStorage.getItem('SHADOWFORGE_BACKEND_URL');
      const storedKeys = await AsyncStorage.getItem('SHADOWFORGE_API_KEYS');
      
      if (storedToken) setToken(storedToken);
      if (storedUrl) setBackendUrl(storedUrl);
      if (storedKeys) setApiKeys(JSON.parse(storedKeys));

      // Start Boot/Wake-up Sequence
      const wakeup = async () => {
        const messages = [
          'Awakening AI Brain...',
          'Establishing Secure Link...',
          'Syncing Neural Paths...',
          'Bypassing Firewalls...'
        ];
        let i = 0;
        const msgInterval = setInterval(() => {
          setBootMessage(messages[i % messages.length]);
          i++;
        }, 3000);

        const tryWake = async () => {
          try {
            await checkHealth();
            clearInterval(msgInterval);
            setIsBooting(false);
          } catch (e) {
            setTimeout(tryWake, 5000);
          }
        };
        tryWake();
      };
      wakeup();
    };
    loadConfig();
  }, []);

  const saveSettings = async () => {
    await AsyncStorage.setItem('SHADOWFORGE_BACKEND_URL', backendUrl);
    await AsyncStorage.setItem('SHADOWFORGE_API_KEYS', JSON.stringify(apiKeys));
    setShowSettings(false);
    // Refresh connection
    if (token) initSocket(token);
  };

  const handleBind = async (newToken) => {
    await AsyncStorage.setItem('DEVICE_TOKEN', newToken);
    setToken(newToken);
    initSocket(newToken);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />
      
      {isBooting ? (
        <View style={styles.bootContainer}>
          <ActivityIndicator size="large" color="#3b82f6" />
          <Zap size={48} color="#3b82f6" style={{ marginTop: 20 }} />
          <Text style={styles.bootTitle}>SHADOWFORGE</Text>
          <Text style={styles.bootSubtitle}>{bootMessage}</Text>
        </View>
      ) : examMode ? (
        <ExamCameraScreen 
          token={token} 
          apiKeys={apiKeys}
          onClose={() => setExamMode(false)} 
        />
      ) : (
        <View style={styles.content}>
          <View style={styles.topBar}>
             <Text style={styles.brand}>SF_OS</Text>
             <TouchableOpacity onPress={() => setShowSettings(true)}>
                <SettingsIcon color="#94a3b8" size={24} />
             </TouchableOpacity>
          </View>
          
          <HomeScreen 
            token={token} 
            apiKeys={apiKeys}
            onBind={handleBind} 
            onToggleExam={() => setExamMode(true)} 
          />
          {token && <FloatingAI token={token} apiKeys={apiKeys} />}
        </View>
      )}

      {/* Settings Modal */}
      <Modal visible={showSettings} animationType="slide" transparent={true}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
               <Text style={styles.modalTitle}>Core Config</Text>
               <TouchableOpacity onPress={() => setShowSettings(false)}>
                  <X color="#94a3b8" size={24} />
               </TouchableOpacity>
            </View>

            <View style={styles.settingGroup}>
               <View style={styles.labelRow}>
                  <Globe size={14} color="#3b82f6" />
                  <Text style={styles.label}>Backend URL</Text>
               </View>
               <TextInput 
                 style={styles.input}
                 value={backendUrl}
                 onChangeText={setBackendUrl}
                 placeholder="https://app.onrender.com"
                 placeholderTextColor="#475569"
               />
            </View>

            <View style={styles.settingGroup}>
               <View style={styles.labelRow}>
                  <Key size={14} color="#3b82f6" />
                  <Text style={styles.label}>Groq API Key</Text>
               </View>
               <TextInput 
                 style={styles.input}
                 value={apiKeys.GROQ_API_KEY}
                 onChangeText={v => setApiKeys({...apiKeys, GROQ_API_KEY: v})}
                 secureTextEntry
                 placeholder="gsk_..."
                 placeholderTextColor="#475569"
               />
            </View>

            <TouchableOpacity style={styles.saveBtn} onPress={saveSettings}>
               <Text style={styles.saveBtnText}>Save & Sync</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  bootContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0f172a' },
  bootTitle: { color: '#fff', fontSize: 24, fontWeight: 'bold', letterSpacing: 5, marginTop: 20 },
  bootSubtitle: { color: '#3b82f6', marginTop: 10, fontFamily: 'monospace', opacity: 0.8 },
  content: { flex: 1 },
  topBar: { flexDirection: 'row', justifyContent: 'space-between', padding: 15, alignItems: 'center' },
  brand: { color: '#3b82f6', fontWeight: '900', fontSize: 18 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#1e293b', borderTopLeftRadius: 30, borderTopRightRadius: 30, padding: 30 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  modalTitle: { color: '#fff', fontSize: 20, fontWeight: 'bold' },
  settingGroup: { marginBottom: 20 },
  labelRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 5 },
  label: { color: '#94a3b8', fontSize: 12, fontWeight: 'bold', textTransform: 'uppercase' },
  input: { backgroundColor: '#0f172a', borderRadius: 10, padding: 12, color: '#fff', borderWidth: 1, borderColor: '#334155' },
  saveBtn: { backgroundColor: '#3b82f6', padding: 15, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  saveBtnText: { color: '#fff', fontWeight: 'bold' }
});
