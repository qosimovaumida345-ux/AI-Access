import React, { useRef, useState } from 'react';
import { View, Text, StyleSheet, Animated, PanResponder, TouchableOpacity } from 'react-native';
import { Sparkles, X } from 'lucide-react-native';

export default function FloatingAI() {
  const pan = useRef(new Animated.ValueXY()).current;
  const [expanded, setExpanded] = useState(false);

  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: () => !expanded,
      onPanResponderGrant: () => {
        pan.setOffset({
          x: pan.x._value,
          y: pan.y._value
        });
      },
      onPanResponderMove: Animated.event(
        [null, { dx: pan.x, dy: pan.y }],
        { useNativeDriver: false }
      ),
      onPanResponderRelease: () => {
        pan.flattenOffset();
      }
    })
  ).current;

  return (
    <Animated.View
      style={[
        styles.floatingContainer,
        { transform: [{ translateX: pan.x }, { translateY: pan.y }] }
      ]}
      {...panResponder.panHandlers}
    >
      {!expanded ? (
        <TouchableOpacity 
          style={styles.circleBtn} 
          onPress={() => setExpanded(true)}
          activeOpacity={0.8}
        >
          <Sparkles color="#fff" size={24} />
        </TouchableOpacity>
      ) : (
        <View style={styles.expandedPanel}>
          <View style={styles.panelHeader}>
             <Text style={styles.panelTitle}>AI Assistant Ready</Text>
             <TouchableOpacity onPress={() => setExpanded(false)}>
                <X color="#94a3b8" size={20} />
             </TouchableOpacity>
          </View>
          <Text style={styles.panelSubtitle}>Listening for audio commands or text logic...</Text>
          <View style={styles.micArea}>
            <Text style={styles.micIcon}>🎙️</Text>
          </View>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  floatingContainer: {
    position: 'absolute',
    bottom: 100,
    right: 20,
    zIndex: 9999,
  },
  circleBtn: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#3b82f6',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#3b82f6',
    shadowOpacity: 0.6,
    shadowRadius: 15,
    elevation: 8,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.2)'
  },
  expandedPanel: {
    width: 250,
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    borderRadius: 20,
    padding: 15,
    borderWidth: 1,
    borderColor: '#3b82f6',
    shadowColor: '#000',
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 10,
  },
  panelHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10
  },
  panelTitle: { color: '#3b82f6', fontWeight: 'bold' },
  panelSubtitle: { color: '#94a3b8', fontSize: 12 },
  micArea: {
    marginTop: 15,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(59, 130, 246, 0.2)',
    height: 60,
    borderRadius: 30
  },
  micIcon: { fontSize: 24 }
});
