import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, SafeAreaView, StatusBar } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import HomeScreen from './src/screens/HomeScreen';
import FloatingAI from './src/components/FloatingAI';
import ExamCameraScreen from './src/screens/ExamCameraScreen';
import { initSocket } from './src/utils/api';

export default function App() {
  const [token, setToken] = useState(null);
  const [examMode, setExamMode] = useState(false);

  useEffect(() => {
    // Check if device is bound
    const loadToken = async () => {
      const storedToken = await AsyncStorage.getItem('DEVICE_TOKEN');
      if (storedToken) {
        setToken(storedToken);
        initSocket(storedToken);
      }
    };
    loadToken();
  }, []);

  const handleBind = async (newToken) => {
    await AsyncStorage.setItem('DEVICE_TOKEN', newToken);
    setToken(newToken);
    initSocket(newToken);
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />
      
      {/* If exam mode is active, we show the specialized Exam Screen (Camera + Overlay) */}
      {examMode ? (
        <ExamCameraScreen 
          token={token} 
          onClose={() => setExamMode(false)} 
        />
      ) : (
        <View style={styles.content}>
          <HomeScreen 
            token={token} 
            onBind={handleBind} 
            onToggleExam={() => setExamMode(true)} 
          />
          {/* Persistent Floating AI Assistant (Always top unless in pure exam mode) */}
          {token && <FloatingAI token={token} />}
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a', // Tailwind slate-900
  },
  content: {
    flex: 1,
    position: 'relative'
  }
});
