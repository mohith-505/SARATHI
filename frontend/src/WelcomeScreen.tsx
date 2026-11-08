import React, { useState, useEffect, useCallback } from "react";
import "./WelcomeScreen.css";
import defaultWelcomeImg from "./assets/sarathi-welcome.png";

interface WelcomeScreenProps {
  onEnter: () => void;
  autoTransitionDelay?: number; // milliseconds, 0 = disabled
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onEnter,
  autoTransitionDelay = 4500,
}) => {
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Keyboard navigation: Enter / Space / Escape opens SARATHI
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " " || e.key === "Escape") {
        e.preventDefault();
        onEnter();
      }
    },
    [onEnter]
  );

  useEffect(() => {
    // Auto-transition to HUD after delay if not dismissed
    let autoTimer: ReturnType<typeof setTimeout> | null = null;
    if (autoTransitionDelay > 0) {
      autoTimer = setTimeout(() => {
        onEnter();
      }, autoTransitionDelay);
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      if (autoTimer) clearTimeout(autoTimer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onEnter, autoTransitionDelay, handleKeyDown]);

  const handleImageError = () => {
    const errorMsg = "Unable to load branding asset from 'assets/branding/sarathi-welcome.png'. Please verify the file exists.";
    console.error("[SARATHI WelcomeScreen]", errorMsg);
    setLoadError(errorMsg);
  };

  return (
    <div
      className={`sarathi-welcome-overlay ${isLoaded ? "visible" : ""}`}
      onClick={onEnter}
      title="Click anywhere to enter SARATHI"
    >
      <div
        className="sarathi-window-container"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Original Authentic Artwork — Pure 1024x322 Aspect Ratio */}
        <div className="sarathi-artwork-frame" onClick={onEnter}>
          {loadError ? (
            <div className="sarathi-asset-error">
              <div className="error-title">SARATHI ~ Asset Missing</div>
              <p>{loadError}</p>
              <button className="error-retry-btn" onClick={onEnter}>
                Continue to SARATHI HUD
              </button>
            </div>
          ) : (
            <img
              src={defaultWelcomeImg || "/assets/branding/sarathi-welcome.png"}
              alt="SARATHI ~ Your AI Companion"
              className="sarathi-original-img"
              onLoad={() => setIsLoaded(true)}
              onError={handleImageError}
            />
          )}

          {/* Interactive Top-Right Window Controls Hotspots mapped to the artwork */}
          <div className="sarathi-hotspots-bar">
            <button
              className="sarathi-hotspot-btn hotspot-min"
              onClick={onEnter}
              title="Minimize / Enter SARATHI"
              aria-label="Minimize"
            />
            <button
              className="sarathi-hotspot-btn hotspot-max"
              onClick={(e) => {
                e.stopPropagation();
                if (!document.fullscreenElement) {
                  document.documentElement.requestFullscreen().catch(() => {});
                } else {
                  document.exitFullscreen().catch(() => {});
                }
              }}
              title="Toggle Fullscreen"
              aria-label="Maximize"
            />
            <button
              className="sarathi-hotspot-btn hotspot-close"
              onClick={onEnter}
              title="Enter SARATHI"
              aria-label="Close"
            />
          </div>
        </div>

        {/* Restrained Launch Action Hint */}
        <div className="sarathi-entry-bar">
          <button
            className="sarathi-launch-btn"
            onClick={onEnter}
            aria-label="Launch SARATHI"
          >
            <span>ENTER SARATHI</span>
            <span className="key-hint">↵ Enter</span>
          </button>
          <div className="sarathi-sub-hint">Click anywhere or press Enter to begin</div>
        </div>
      </div>
    </div>
  );
};

export default WelcomeScreen;
