import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Dimensions } from 'react-native';

const { width, height } = Dimensions.get('window');

// Extremely basic implementation of Exam camera screen for the initial version
// In a full environment, you would use expo-camera
export default function ExamCameraScreen({ token, onClose }) {
  const [answer, setAnswer] = React.useState('');

  // Pretend function for capturing and sending image
  const captureAndAnalyze = () => {
    // Usually uses expo-camera takePictureAsync
    setAnswer("Analyzing visual buffer...");
    setTimeout(() => {
      setAnswer("The answer to the question is: Mitochondria (Option B)");
    }, 2000);
  };

  return (
    <View style={styles.container}>
      {/* Fake Camera Viewfinder */}
      <View style={styles.cameraView}>
        <Text style={styles.cameraText}>[ Camera Viewfinder ]</Text>
        <Text style={styles.cameraHint}>Point at the screen/paper</Text>
      </View>

      {/* Persistent Invisible Overlay Area */}
      <View style={styles.overlayArea} pointerEvents="none">
        {answer ? (
          <View style={styles.redAnswerBox}>
             <Text style={styles.redAnswerText}>{answer}</Text>
          </View>
        ) : null}
      </View>

      {/* Controllers */}
      <View style={styles.controls}>
        <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
          <Text style={styles.closeText}>Deactivate Exam Mode</Text>
        </TouchableOpacity>

        {/* This functions like the SHIFT key on Desktop */}
        <TouchableOpacity style={styles.captureBtn} onPress={captureAndAnalyze}>
           <Text style={styles.captureText}>Parse Screen</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  cameraView: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  cameraText: { color: 'rgba(255,255,255,0.3)', fontSize: 24, fontWeight: 'bold' },
  cameraHint: { color: 'rgba(255,255,255,0.4)', marginTop: 10 },
  overlayArea: {
    position: 'absolute',
    top: 50,
    width: '100%',
    alignItems: 'center',
    zIndex: 999
  },
  redAnswerBox: {
    backgroundColor: 'rgba(0,0,0,0.8)',
    borderWidth: 1,
    borderColor: '#ff3333',
    padding: 15,
    borderRadius: 8,
    shadowColor: '#ff3333',
    shadowOpacity: 0.8,
    shadowRadius: 10,
    elevation: 10,
    width: '80%'
  },
  redAnswerText: {
    color: '#ff3333',
    fontWeight: 'bold',
    fontSize: 18,
    textAlign: 'center'
  },
  controls: {
    position: 'absolute',
    bottom: 40,
    width: '100%',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20
  },
  closeBtn: {
    backgroundColor: 'rgba(248, 113, 113, 0.2)',
    padding: 15,
    borderRadius: 30,
    borderWidth: 1,
    borderColor: '#f87171'
  },
  closeText: { color: '#f87171', fontWeight: 'bold' },
  captureBtn: {
    backgroundColor: '#3b82f6',
    padding: 15,
    borderRadius: 30,
    width: 150,
    alignItems: 'center'
  },
  captureText: { color: '#fff', fontWeight: 'bold' }
});
