#!/usr/bin/env python3
"""
Monitor wheel build size and track changes over time.
Helps detect package bloat and unexpected size increases.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
import hashlib


def get_wheel_info(wheel_path):
    """Extract information about wheel file."""
    wheel = Path(wheel_path)
    if not wheel.exists():
        raise FileNotFoundError(f"Wheel not found: {wheel_path}")
    
    # Get file size in bytes and MB
    size_bytes = wheel.stat().st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    
    # Calculate file hash for integrity
    with open(wheel, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    
    return {
        'filename': wheel.name,
        'size_bytes': size_bytes,
        'size_mb': size_mb,
        'hash': file_hash,
        'timestamp': datetime.utcnow().isoformat(),
    }


def load_size_history(history_file):
    """Load historical size data."""
    if not Path(history_file).exists():
        return []
    
    try:
        with open(history_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_size_history(history_file, history_data):
    """Save historical size data."""
    # Keep only last 50 entries to avoid bloating
    history_data = history_data[-50:]
    
    Path(history_file).parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, 'w') as f:
        json.dump(history_data, f, indent=2)


def analyze_size_trend(history_data, current_info):
    """Analyze size trends and provide insights."""
    if len(history_data) == 0:
        return {
            'trend': 'baseline',
            'message': f"📏 First measurement: {current_info['size_mb']}MB",
            'alert': False
        }
    
    # Get recent measurements (last 5)
    recent = history_data[-5:]
    avg_recent_size = sum(entry['size_mb'] for entry in recent) / len(recent)
    
    # Calculate percentage change
    size_change = current_info['size_mb'] - avg_recent_size
    pct_change = (size_change / avg_recent_size) * 100 if avg_recent_size > 0 else 0
    
    # Determine trend and alerts
    if abs(pct_change) < 2:
        trend = 'stable'
        message = f"📏 Size stable: {current_info['size_mb']}MB (±{pct_change:+.1f}%)"
        alert = False
    elif pct_change > 10:
        trend = 'major_increase'
        message = f"🚨 Major size increase: {current_info['size_mb']}MB (+{pct_change:.1f}%) - investigate package bloat"
        alert = True
    elif pct_change > 5:
        trend = 'increase'
        message = f"⚠️ Size increased: {current_info['size_mb']}MB (+{pct_change:.1f}%)"
        alert = True
    elif pct_change < -10:
        trend = 'major_decrease'
        message = f"📉 Major size decrease: {current_info['size_mb']}MB ({pct_change:.1f}%) - good optimization!"
        alert = False
    else:
        trend = 'minor_change'
        message = f"📏 Size changed: {current_info['size_mb']}MB ({pct_change:+.1f}%)"
        alert = False
    
    return {
        'trend': trend,
        'message': message,
        'alert': alert,
        'change_mb': size_change,
        'change_pct': pct_change,
    }


def main():
    """Monitor wheel build size."""
    if len(sys.argv) != 2:
        print("Usage: python monitor_build_size.py <wheel_file>")
        sys.exit(1)
    
    wheel_path = sys.argv[1]
    history_file = Path(__file__).parent / '..' / 'build_size_history.json'
    
    try:
        # Get current wheel info
        current_info = get_wheel_info(wheel_path)
        
        # Load historical data
        history_data = load_size_history(history_file)
        
        # Analyze trend
        analysis = analyze_size_trend(history_data, current_info)
        
        # Print results
        print("🔍 Build Size Monitor")
        print("=" * 50)
        print(f"Wheel: {current_info['filename']}")
        print(f"Size: {current_info['size_mb']}MB ({current_info['size_bytes']:,} bytes)")
        print(f"Hash: {current_info['hash']}")
        print()
        print(analysis['message'])
        
        if analysis['alert']:
            print()
            print("💡 Recommendations:")
            if 'increase' in analysis['trend']:
                print("  • Check if new dependencies were added")
                print("  • Review data files or assets included in package")
                print("  • Consider using MANIFEST.in to exclude unnecessary files")
                print("  • Verify no compiled binaries or large files are included")
        
        # Update history
        history_data.append(current_info)
        save_size_history(history_file, history_data)
        
        # Exit with error code if major size increase
        if analysis['trend'] == 'major_increase':
            print(f"\n❌ Build size increased by {analysis['change_pct']:.1f}% - review required!")
            sys.exit(1)
        
        print(f"\n✅ Build size monitoring complete")
        
    except Exception as e:
        print(f"❌ Error monitoring build size: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()