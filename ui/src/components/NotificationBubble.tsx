import React, { useEffect, useState, forwardRef } from 'react'
import { motion } from 'framer-motion'
import { X, ExternalLink } from 'lucide-react'
import { Notification } from '../types/notification'
import { formatReadableTokenAmount, cn } from '../lib/utils'
import InternalLink from './InternalLink'

// Kick drum sound generator using Web Audio API
const playKickSound = () => {
  try {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const now = audioContext.currentTime
    
    // Create oscillator for the bass thump
    const osc = audioContext.createOscillator()
    const oscGain = audioContext.createGain()
    
    // Create noise for the attack/click
    const noiseBufferSize = audioContext.sampleRate * 0.02 // 20ms of noise
    const noiseBuffer = audioContext.createBuffer(1, noiseBufferSize, audioContext.sampleRate)
    const noiseData = noiseBuffer.getChannelData(0)
    
    // Generate brown noise (more bass-heavy than white noise)
    let lastOut = 0
    for (let i = 0; i < noiseBufferSize; i++) {
      const white = Math.random() * 2 - 1
      noiseData[i] = (lastOut + (0.02 * white)) / 1.02
      lastOut = noiseData[i]
      noiseData[i] *= 3.5 // boost volume
    }
    
    const noiseSource = audioContext.createBufferSource()
    const noiseGain = audioContext.createGain()
    const noiseFilter = audioContext.createBiquadFilter()
    
    noiseSource.buffer = noiseBuffer
    
    // Configure low-pass filter for kick drum click
    noiseFilter.type = 'lowpass'
    noiseFilter.frequency.value = 1000
    noiseFilter.Q.value = 1
    
    // Kick drum frequency sweep (starts high, drops to bass)
    osc.type = 'sine'
    osc.frequency.setValueAtTime(150, now)
    osc.frequency.exponentialRampToValueAtTime(40, now + 0.1) // Drop to deep bass
    
    // Kick drum envelope (punchy attack, longer decay)
    oscGain.gain.setValueAtTime(0, now)
    oscGain.gain.linearRampToValueAtTime(0.8, now + 0.005) // Punchy attack
    oscGain.gain.exponentialRampToValueAtTime(0.001, now + 0.2) // Longer decay
    
    // Noise envelope (quick attack for the "click")
    noiseGain.gain.setValueAtTime(0, now)
    noiseGain.gain.linearRampToValueAtTime(0.4, now + 0.002)
    noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.05)
    
    // Connect the kick drum chain
    osc.connect(oscGain)
    oscGain.connect(audioContext.destination)
    
    // Connect the noise/click chain
    noiseSource.connect(noiseFilter)
    noiseFilter.connect(noiseGain)
    noiseGain.connect(audioContext.destination)
    
    // Play both components
    osc.start(now)
    osc.stop(now + 0.2)
    noiseSource.start(now)
    noiseSource.stop(now + 0.05)
    
  } catch (error) {
    // Silently fail if Web Audio API not supported
    console.debug('Audio notification not available:', error)
  }
}

interface NotificationBubbleProps {
  notification: Notification
  onDismiss: (id: string) => void
  index: number
}

const NotificationBubble = forwardRef<HTMLDivElement, NotificationBubbleProps>(({
  notification,
  onDismiss,
  index
}, ref) => {
  const [progress, setProgress] = useState(100)

  // Play kick drum sound on mount (only for new notifications)
  useEffect(() => {
    if (index === 0) { // Only play sound for the topmost (newest) notification
      // Check if user has sound enabled in localStorage
      const soundEnabled = localStorage.getItem('notificationSoundEnabled') !== 'false'
      if (soundEnabled) {
        playKickSound()
      }
    }
  }, [index])

  // Progress bar animation
  useEffect(() => {
    const duration = 10000 // 10 seconds
    const interval = 100 // Update every 100ms
    const decrement = (interval / duration) * 100

    const timer = setInterval(() => {
      setProgress(prev => {
        const newProgress = prev - decrement
        if (newProgress <= 0) {
          // Use setTimeout to avoid setState during render
          setTimeout(() => onDismiss(notification.id), 0)
          return 0
        }
        return newProgress
      })
    }, interval)

    return () => clearInterval(timer)
  }, [notification.id, onDismiss])

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'kick':
        return '🚀'
      case 'take':
        return '💰'
      case 'deploy':
        return '🏭'
      default:
        return '📢'
    }
  }

  const getEventTitle = (type: string) => {
    switch (type) {
      case 'kick':
        return 'New Auction Round'
      case 'take':
        return 'Take'
      case 'deploy':
        return 'New Auction Deployed'
      default:
        return 'Event'
    }
  }

  const formatAddress = (address: string) => {
    if (!address) return 'N/A'
    return `${address.slice(0, 6)}..${address.slice(-4)}`
  }

  const getExplorerLink = (txHash: string, chainId: number) => {
    if (!txHash || chainId === 31337) return null

    const explorers: Record<number, string> = {
      1: 'https://etherscan.io/tx/',
      137: 'https://polygonscan.com/tx/',
      42161: 'https://arbiscan.io/tx/',
      10: 'https://optimistic.etherscan.io/tx/',
      8453: 'https://basescan.org/tx/'
    }

    const explorer = explorers[chainId]
    return explorer ? `${explorer}${txHash}` : null
  }

  const renderContent = () => {
    const { content, type } = notification

    switch (type) {
      case 'kick':
        return (
          <div className="space-y-1 text-sm">
            <div className="text-gray-300">Chain: {content.chainName}</div>
            {content.roundId && (
              <div className="text-gray-300">
                Round: <InternalLink 
                  to={`/round/${content.chainId}/${content.auctionAddress}/${content.roundId}`}
                  className="text-primary-400 hover:text-primary-300"
                >
                  #{content.roundId}
                </InternalLink>
              </div>
            )}
            <div className="text-gray-300">
              Auction: <InternalLink 
                to={`/auction/${content.chainId}/${content.auctionAddress}`}
                className="text-primary-400 hover:text-primary-300"
              >
                {formatAddress(content.auctionAddress)}
              </InternalLink>
            </div>
            {content.fromTokenSymbol && content.wantTokenSymbol && (
              <div className="text-gray-300">
                Pair: {content.fromTokenSymbol} → {content.wantTokenSymbol}
              </div>
            )}
            {content.initialAvailable && content.fromTokenSymbol && (
              <div className="text-gray-300">
                Available: {formatReadableTokenAmount(content.initialAvailable)} {content.fromTokenSymbol}
              </div>
            )}
          </div>
        )

      case 'take':
        return (
          <div className="space-y-1 text-sm">
            {content.taker && (
              <div className="text-gray-300">
                Taker: <InternalLink 
                  to={`/taker/${content.taker}`}
                  className="text-primary-400 hover:text-primary-300"
                >
                  {formatAddress(content.taker)}
                </InternalLink>
              </div>
            )}
            {content.amountTaken && content.fromTokenSymbol && (
              <div className="text-gray-300">
                Bought: {formatReadableTokenAmount(content.amountTaken)} {content.fromTokenSymbol}
              </div>
            )}
            {content.amountPaid && content.wantTokenSymbol && (
              <div className="text-gray-300">
                Paid: {formatReadableTokenAmount(content.amountPaid)} {content.wantTokenSymbol}
              </div>
            )}
            <div className="text-gray-300">
              {content.roundId ? (
                <>
                  <InternalLink 
                    to={`/round/${content.chainId}/${content.auctionAddress}/${content.roundId}`}
                    className="text-primary-400 hover:text-primary-300"
                  >
                    Round #{content.roundId}
                  </InternalLink>
                  {' on '}{content.chainName}
                </>
              ) : (
                `Chain: ${content.chainName}`
              )}
            </div>
          </div>
        )

      case 'deploy':
        return (
          <div className="space-y-1 text-sm">
            <div className="text-gray-300">Chain: {content.chainName}</div>
            <div className="text-gray-300">
              Address: <InternalLink 
                to={`/auction/${content.chainId}/${content.auctionAddress}`}
                className="text-primary-400 hover:text-primary-300"
              >
                {formatAddress(content.auctionAddress)}
              </InternalLink>
            </div>
            {content.wantTokenSymbol && (
              <div className="text-gray-300">Want Token: {content.wantTokenSymbol}</div>
            )}
            {content.version && (
              <div className="text-gray-300">Version: {content.version}</div>
            )}
            {content.decayRate && (
              <div className="text-gray-300">
                Decay Rate: {(parseFloat(content.decayRate) * 100).toFixed(2)}%/hr
              </div>
            )}
          </div>
        )

      default:
        return <div className="text-sm text-gray-300">Unknown event type</div>
    }
  }

  const explorerLink = getExplorerLink(notification.content.txHash || '', notification.content.chainId)

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: 300, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 300, scale: 0.95 }}
      transition={{ 
        type: "spring", 
        stiffness: 400, 
        damping: 30,
        mass: 0.8
      }}
      className={cn(
        "relative w-80 bg-gray-900/90 backdrop-blur-md border border-gray-700",
        "rounded-lg shadow-2xl p-4 space-y-3"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getEventIcon(notification.type)}</span>
          <span className="font-semibold text-gray-100 text-sm">
            {getEventTitle(notification.type)}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          {explorerLink && (
            <a
              href={explorerLink}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 rounded hover:bg-gray-700/50 text-gray-400 hover:text-gray-300 transition-colors"
              title="View on explorer"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <button
            onClick={() => onDismiss(notification.id)}
            className="p-1 rounded hover:bg-gray-700/50 text-gray-400 hover:text-gray-300 transition-colors"
            title="Dismiss"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Content */}
      {renderContent()}

      {/* Progress bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-800 rounded-b-lg overflow-hidden">
        <div
          className="h-full bg-primary-500 transition-all duration-100 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>
    </motion.div>
  )
})

NotificationBubble.displayName = 'NotificationBubble'

export default NotificationBubble