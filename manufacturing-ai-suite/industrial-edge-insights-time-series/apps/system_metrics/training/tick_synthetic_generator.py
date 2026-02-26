#!/usr/bin/env python3
"""
Synthetic Dataset Generator for TICK Stack with Predictive Maintenance
Generates point-by-point metrics compatible with Kapacitor processing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')

class TICKSyntheticGenerator:
    def __init__(self, start_time='2026-02-17T00:00:00', duration_hours=24, interval_seconds=10):
        """
        Initialize the generator
        
        Args:
            start_time: Start timestamp
            duration_hours: Duration in hours
            interval_seconds: Sampling interval in seconds
        """
        self.start_time = pd.to_datetime(start_time, utc=True)
        self.duration_hours = duration_hours
        self.interval_seconds = interval_seconds
        self.num_points = int(duration_hours * 3600 / interval_seconds)
        
        # System configuration
        self.num_hosts = 2
        self.containers_per_host = 5
        self.total_containers = self.num_hosts * self.containers_per_host
        self.cpu_cores = 32
        self.total_mem_mb = 16384
        self.total_swap_mb = 8192
        self.total_disk_gb = 2000
        
        # Anomaly and failure tracking
        self.failure_time = None
        self.anomaly_windows = []
        
    def generate_timestamps(self):
        """Generate timestamp series"""
        return pd.date_range(
            start=self.start_time,
            periods=self.num_points,
            freq=f'{self.interval_seconds}s'
        )
    
    def generate_base_cpu_metrics(self, timestamps):
        """Generate CPU metrics (point-by-point compatible)"""
        n = len(timestamps)
        
        # Time-based patterns
        hours = np.array([ts.hour for ts in timestamps])
        day_pattern = 0.3 + 0.4 * np.sin((hours - 6) * np.pi / 12)  # Peak at 12-18h
        
        # Base CPU usage
        cpu_idle_base = 70 + 15 * day_pattern
        cpu_user_base = 15 + 10 * day_pattern
        cpu_system_base = 5 + 3 * day_pattern
        cpu_iowait_base = np.ones(n) * 1.5
        
        # Add noise
        cpu_idle = np.clip(cpu_idle_base + np.random.normal(0, 3, n), 0, 100)
        cpu_user = np.clip(cpu_user_base + np.random.normal(0, 2, n), 0, 100 - cpu_idle)
        cpu_system = np.clip(cpu_system_base + np.random.normal(0, 1, n), 0, 100 - cpu_idle - cpu_user)
        cpu_iowait = np.clip(cpu_iowait_base + np.random.normal(0, 0.5, n), 0, 100)
        
        # Total CPU percentage (100 - idle)
        cpu_total_pct = 100 - cpu_idle
        
        return {
            'cpu_total_pct': cpu_total_pct,
            'cpu_user_pct': cpu_user,
            'cpu_system_pct': cpu_system,
            'cpu_iowait_pct': cpu_iowait,
            'cpu_idle_pct': cpu_idle
        }
    
    def generate_memory_metrics(self, timestamps, cpu_total):
        """Generate memory metrics (correlated with CPU)"""
        n = len(timestamps)
        
        # Memory baseline with correlation to CPU
        mem_base = 50 + 0.3 * cpu_total
        mem_used_pct = np.clip(mem_base + np.random.normal(0, 5, n), 20, 95)
        mem_used_mb = (mem_used_pct / 100 * self.total_mem_mb).astype(int)
        
        # Swap usage (low under normal conditions)
        swap_used_pct = np.clip(np.random.exponential(2, n) + 5, 0, 30)
        
        return {
            'mem_used_mb': mem_used_mb,
            'mem_used_pct': mem_used_pct,
            'swap_used_pct': swap_used_pct
        }
    
    def generate_disk_metrics(self, timestamps, cpu_total):
        """Generate disk I/O metrics"""
        n = len(timestamps)
        
        # Disk usage (slowly growing)
        disk_used_base = 50 + np.linspace(0, 5, n)  # Grows 5% over time
        disk_used_pct = disk_used_base + np.random.normal(0, 1, n)
        
        # Disk I/O correlated with CPU activity
        io_factor = cpu_total / 100
        disk_read_bps = np.clip(
            io_factor * np.random.exponential(1e6, n),
            50000, 5e6
        ).astype(int)
        disk_write_bps = np.clip(
            io_factor * np.random.exponential(8e5, n),
            30000, 3e6
        ).astype(int)
        
        # Disk latency (increases with I/O)
        base_latency = 5 + (disk_read_bps + disk_write_bps) / 2e5
        disk_latency_ms = base_latency + np.random.lognormal(0, 0.3, n)
        
        # IOPS
        disk_iops = ((disk_read_bps + disk_write_bps) / 4096 / 10).astype(int)
        
        return {
            'disk_used_pct': disk_used_pct,
            'disk_read_bps': disk_read_bps,
            'disk_write_bps': disk_write_bps,
            'disk_latency_ms': disk_latency_ms,
            'disk_iops': disk_iops
        }
    
    def generate_network_metrics(self, timestamps, cpu_total):
        """Generate network metrics"""
        n = len(timestamps)
        
        # Network traffic correlated with CPU
        net_factor = cpu_total / 100
        net_in_bps = np.clip(
            net_factor * np.random.exponential(2e5, n),
            10000, 1e6
        ).astype(int)
        net_out_bps = np.clip(
            net_factor * np.random.exponential(1.5e5, n),
            8000, 8e5
        ).astype(int)
        
        # Network error rate (very low normally)
        net_err_rate = np.random.exponential(0.0001, n)
        
        return {
            'net_in_bps': net_in_bps,
            'net_out_bps': net_out_bps,
            'net_err_rate': net_err_rate
        }
    
    def generate_system_metrics(self, timestamps, cpu_total):
        """Generate system-level metrics"""
        n = len(timestamps)
        
        # Load average correlated with CPU
        load1 = cpu_total / 100 * self.cpu_cores * 0.5 + np.random.normal(0, 1, n)
        load1 = np.clip(load1, 0, self.cpu_cores * 2)
        
        # Running processes
        proc_running_base = 30 + cpu_total / 100 * 20
        proc_running = np.clip(proc_running_base + np.random.normal(0, 5, n), 10, 100).astype(int)
        
        return {
            'load1': load1,
            'proc_running': proc_running
        }
    
    def generate_container_metrics(self, timestamps, cpu_total, mem_used_pct):
        """Generate container-level aggregated metrics"""
        n = len(timestamps)
        
        # Container CPU usage (aggregate across all containers)
        # Individual containers use cpu_total/num_containers with variation
        ctr_cpu_base = cpu_total / self.total_containers * np.random.uniform(0.8, 1.2, n)
        ctr_cpu_total_pct = np.clip(ctr_cpu_base + np.random.normal(0, 5, n), 0, 100)
        
        # Container memory usage (as percentage of limit)
        ctr_mem_base = mem_used_pct / self.total_containers * np.random.uniform(0.7, 1.3, n)
        ctr_mem_used_pct_of_limit = np.clip(ctr_mem_base + np.random.normal(0, 10, n), 10, 95)
        
        # Container health (normally all healthy)
        ctr_unhealthy_count = np.zeros(n, dtype=int)
        ctr_exited_count = np.zeros(n, dtype=int)
        
        return {
            'ctr_cpu_total_pct': ctr_cpu_total_pct,
            'ctr_mem_used_pct_of_limit': ctr_mem_used_pct_of_limit,
            'ctr_unhealthy_count': ctr_unhealthy_count,
            'ctr_exited_count': ctr_exited_count
        }
    
    def inject_anomalies(self, df):
        """Inject realistic anomalies and failures"""
        print("Injecting anomalies and degradation patterns...")
        
        n = len(df)
        
        # Initialize anomaly tracking columns
        df['anomaly'] = 0
        df['anomaly_type'] = 0
        df['failure'] = 0
        df['event_cpu_active'] = 0
        df['event_leak_active'] = 0
        df['event_io_active'] = 0
        df['degradation_active'] = 0
        
        # Randomly select failure time (last 20-30% of timeline)
        failure_idx = random.randint(int(n * 0.7), int(n * 0.85))
        self.failure_time = df.index[failure_idx]
        df.loc[failure_idx:, 'failure'] = 1
        
        # Calculate time to failure
        time_to_failure = []
        for idx in range(n):
            if idx < failure_idx:
                ttf = (failure_idx - idx) * self.interval_seconds / 60  # minutes
            else:
                ttf = 0
            time_to_failure.append(ttf)
        df['ttf_minutes'] = time_to_failure
        
        # Failure within prediction horizon (60 minutes)
        df['failure_within_horizon'] = (df['ttf_minutes'] > 0) & (df['ttf_minutes'] <= 60)
        
        # Inject different anomaly types
        anomaly_types = [
            'cpu_spike',
            'memory_leak', 
            'io_bottleneck',
            'network_congestion',
            'container_crash',
        ]
        
        num_anomalies = random.randint(5, 10)
        
        for _ in range(num_anomalies):
            # Random anomaly type
            anom_type = random.choice(anomaly_types)
            
            # Random start time (not too close to beginning or failure)
            start_idx = random.randint(int(n * 0.1), min(failure_idx - 100, int(n * 0.6)))
            
            # Duration based on type
            if anom_type == 'cpu_spike':
                duration = random.randint(30, 180)  # 5-30 minutes at 10s intervals
                end_idx = min(start_idx + duration, n - 1)
                
                df.loc[start_idx:end_idx, 'cpu_total_pct'] = np.clip(
                    df.loc[start_idx:end_idx, 'cpu_total_pct'] * np.random.uniform(2, 3, end_idx - start_idx + 1),
                    75, 98
                )
                df.loc[start_idx:end_idx, 'cpu_user_pct'] = np.clip(
                    df.loc[start_idx:end_idx, 'cpu_user_pct'] * 2.5,
                    60, 90
                )
                df.loc[start_idx:end_idx, 'cpu_idle_pct'] = 100 - df.loc[start_idx:end_idx, 'cpu_total_pct']
                df.loc[start_idx:end_idx, 'load1'] = np.clip(
                    df.loc[start_idx:end_idx, 'load1'] * 3,
                    10, self.cpu_cores * 1.5
                )
                df.loc[start_idx:end_idx, 'event_cpu_active'] = 1
                df.loc[start_idx:end_idx, 'anomaly'] = 1
                df.loc[start_idx:end_idx, 'anomaly_type'] = 1  # CPU spike
                
            elif anom_type == 'memory_leak':
                duration = random.randint(360, 1080)  # 1-3 hours
                end_idx = min(start_idx + duration, failure_idx - 10)
                
                # Gradual memory increase
                leak_values = np.linspace(
                    df.loc[start_idx, 'mem_used_pct'],
                    95,
                    end_idx - start_idx + 1
                )
                df.loc[start_idx:end_idx, 'mem_used_pct'] = leak_values
                df.loc[start_idx:end_idx, 'mem_used_mb'] = (leak_values / 100 * self.total_mem_mb).astype(int)
                df.loc[start_idx:end_idx, 'swap_used_pct'] = np.clip(
                    df.loc[start_idx:end_idx, 'swap_used_pct'] * 2 + np.linspace(0, 15, end_idx - start_idx + 1),
                    5, 40
                )
                df.loc[start_idx:end_idx, 'ctr_mem_used_pct_of_limit'] = np.clip(
                    leak_values * 0.8,
                    50, 98
                )
                df.loc[start_idx:end_idx, 'event_leak_active'] = 1
                df.loc[start_idx:end_idx, 'anomaly'] = 1
                df.loc[start_idx:end_idx, 'anomaly_type'] = 2  # Memory leak
                
            elif anom_type == 'io_bottleneck':
                duration = random.randint(120, 540)  # 20-90 minutes
                end_idx = min(start_idx + duration, n - 1)
                
                df.loc[start_idx:end_idx, 'disk_read_bps'] = np.clip(
                    df.loc[start_idx:end_idx, 'disk_read_bps'] * np.random.uniform(5, 10, end_idx - start_idx + 1),
                    1e6, 10e6
                ).astype(int)
                df.loc[start_idx:end_idx, 'disk_write_bps'] = np.clip(
                    df.loc[start_idx:end_idx, 'disk_write_bps'] * np.random.uniform(5, 10, end_idx - start_idx + 1),
                    5e5, 8e6
                ).astype(int)
                df.loc[start_idx:end_idx, 'disk_latency_ms'] = np.clip(
                    df.loc[start_idx:end_idx, 'disk_latency_ms'] * np.random.uniform(3, 8, end_idx - start_idx + 1),
                    20, 100
                )
                df.loc[start_idx:end_idx, 'disk_iops'] = np.clip(
                    df.loc[start_idx:end_idx, 'disk_iops'] * 5,
                    100, 1000
                ).astype(int)
                df.loc[start_idx:end_idx, 'cpu_iowait_pct'] = np.clip(
                    df.loc[start_idx:end_idx, 'cpu_iowait_pct'] * 10,
                    10, 40
                )
                df.loc[start_idx:end_idx, 'event_io_active'] = 1
                df.loc[start_idx:end_idx, 'anomaly'] = 1
                df.loc[start_idx:end_idx, 'anomaly_type'] = 3  # I/O bottleneck
                
            elif anom_type == 'network_congestion':
                duration = random.randint(60, 270)  # 10-45 minutes
                end_idx = min(start_idx + duration, n - 1)
                
                df.loc[start_idx:end_idx, 'net_in_bps'] = np.clip(
                    df.loc[start_idx:end_idx, 'net_in_bps'] * np.random.uniform(5, 12, end_idx - start_idx + 1),
                    5e5, 5e6
                ).astype(int)
                df.loc[start_idx:end_idx, 'net_out_bps'] = np.clip(
                    df.loc[start_idx:end_idx, 'net_out_bps'] * np.random.uniform(5, 12, end_idx - start_idx + 1),
                    4e5, 4e6
                ).astype(int)
                df.loc[start_idx:end_idx, 'net_err_rate'] = np.clip(
                    df.loc[start_idx:end_idx, 'net_err_rate'] * 100 + 0.01,
                    0.001, 0.05
                )
                df.loc[start_idx:end_idx, 'anomaly'] = 1
                df.loc[start_idx:end_idx, 'anomaly_type'] = 4  # Network congestion
                
            elif anom_type == 'container_crash':
                duration = random.randint(6, 30)  # 1-5 minutes
                end_idx = min(start_idx + duration, n - 1)
                
                num_unhealthy = random.randint(1, min(3, self.total_containers))
                df.loc[start_idx:end_idx, 'ctr_unhealthy_count'] = num_unhealthy
                df.loc[start_idx:end_idx, 'ctr_exited_count'] = random.randint(0, num_unhealthy)
                df.loc[start_idx:end_idx, 'anomaly'] = 1
                df.loc[start_idx:end_idx, 'anomaly_type'] = 5  # Container crash
        
        # Progressive degradation leading to failure
        degradation_start = max(0, failure_idx - 360)  # 1 hour before failure
        df.loc[degradation_start:failure_idx, 'degradation_active'] = 1
        
        # Gradual resource exhaustion
        degradation_length = failure_idx - degradation_start
        degradation_factor = np.linspace(1, 2.5, degradation_length + 1)
        
        df.loc[degradation_start:failure_idx, 'cpu_total_pct'] = np.clip(
            df.loc[degradation_start:failure_idx, 'cpu_total_pct'] * degradation_factor,
            50, 99
        )
        df.loc[degradation_start:failure_idx, 'mem_used_pct'] = np.clip(
            df.loc[degradation_start:failure_idx, 'mem_used_pct'] * degradation_factor * 0.8,
            60, 98
        )
        df.loc[degradation_start:failure_idx, 'disk_latency_ms'] = np.clip(
            df.loc[degradation_start:failure_idx, 'disk_latency_ms'] * degradation_factor,
            10, 150
        )
        df.loc[degradation_start:failure_idx, 'load1'] = np.clip(
            df.loc[degradation_start:failure_idx, 'load1'] * degradation_factor,
            5, self.cpu_cores * 2
        )
        
        # At failure point - system collapse
        df.loc[failure_idx:, 'cpu_total_pct'] = np.random.uniform(95, 100, len(df) - failure_idx)
        df.loc[failure_idx:, 'mem_used_pct'] = np.random.uniform(98, 100, len(df) - failure_idx)
        df.loc[failure_idx:, 'ctr_unhealthy_count'] = np.random.randint(
            self.total_containers // 2,
            self.total_containers,
            len(df) - failure_idx
        )
        
        return df
    
    def generate_dataset(self):
        """Generate complete synthetic dataset"""
        print(f"Generating {self.num_points} data points over {self.duration_hours} hours...")
        
        # Generate timestamps
        timestamps = self.generate_timestamps()
        
        # Initialize dataframe
        data = {
            'timestamp': timestamps,
            'hosts': self.num_hosts,
            'containers_total': self.total_containers,
            'total_cpu_cores': self.cpu_cores,
            'total_mem_mb': self.total_mem_mb,
            'total_swap_mb': self.total_swap_mb,
            'total_disk_gb': self.total_disk_gb,
        }
        
        # Generate CPU metrics
        print("Generating CPU metrics...")
        cpu_metrics = self.generate_base_cpu_metrics(timestamps)
        data.update(cpu_metrics)
        
        # Generate memory metrics
        print("Generating memory metrics...")
        mem_metrics = self.generate_memory_metrics(timestamps, cpu_metrics['cpu_total_pct'])
        data.update(mem_metrics)
        
        # Generate disk metrics
        print("Generating disk metrics...")
        disk_metrics = self.generate_disk_metrics(timestamps, cpu_metrics['cpu_total_pct'])
        data.update(disk_metrics)
        
        # Generate network metrics
        print("Generating network metrics...")
        net_metrics = self.generate_network_metrics(timestamps, cpu_metrics['cpu_total_pct'])
        data.update(net_metrics)
        
        # Generate system metrics
        print("Generating system metrics...")
        sys_metrics = self.generate_system_metrics(timestamps, cpu_metrics['cpu_total_pct'])
        data.update(sys_metrics)
        
        # Generate container metrics
        print("Generating container metrics...")
        ctr_metrics = self.generate_container_metrics(
            timestamps,
            cpu_metrics['cpu_total_pct'],
            mem_metrics['mem_used_pct']
        )
        data.update(ctr_metrics)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Inject anomalies and failures
        df = self.inject_anomalies(df)
        
        # Round floating point values
        float_cols = df.select_dtypes(include=['float64']).columns
        df[float_cols] = df[float_cols].round(6)
        
        print(f"\nDataset generated: {len(df)} records")
        print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"Anomalies: {df['anomaly'].sum()} points ({df['anomaly'].sum()/len(df)*100:.2f}%)")
        print(f"Failure occurs at: {df[df['failure'] == 1]['timestamp'].min()}")
        
        return df


def main():
    """Generate synthetic dataset"""
    
    # Configuration
    generator = TICKSyntheticGenerator(
        start_time='2026-02-17T00:00:00',
        duration_hours=24,
        interval_seconds=10
    )
    
    # Generate dataset
    dataset = generator.generate_dataset()
    
    # Display statistics
    print("\n" + "="*60)
    print("DATASET STATISTICS")
    print("="*60)
    print(f"Total records: {len(dataset)}")
    print(f"Anomaly distribution:")
    print(dataset['anomaly_type'].value_counts().sort_index())
    print(f"\nFailure within horizon: {dataset['failure_within_horizon'].sum()} points")
    print(f"Degradation active: {dataset['degradation_active'].sum()} points")
    
    # Save datasets
    output_file = 'tick_synthetic_pm_dataset.csv'
    dataset.to_csv(output_file, index=False)
    print(f"\n✓ Full dataset saved to: {output_file}")
    
    # Create sample for quick testing
    sample_size = min(1000, len(dataset))
    sample_dataset = dataset.sample(n=sample_size, random_state=42)
    sample_file = 'tick_synthetic_pm_sample.csv'
    sample_dataset.to_csv(sample_file, index=False)
    print(f"✓ Sample dataset saved to: {sample_file}")
    
    print("\n" + "="*60)
    print("COLUMN MAPPING TO INFLUXDB")
    print("="*60)
    print("""
Point-by-point metrics (Kapacitor compatible):
  - cpu_*_pct          → cpu measurement
  - mem_used_*         → mem measurement  
  - swap_used_pct      → swap measurement
  - disk_*             → disk/diskio measurements
  - net_*              → net measurement
  - load1              → system measurement
  - proc_running       → processes measurement
  - ctr_*              → docker_container_* measurements
  
ML/Prediction labels (for training):
  - anomaly            → Binary anomaly flag
  - anomaly_type       → Type: 0=normal, 1=cpu, 2=mem, 3=io, 4=net, 5=container
  - failure            → Binary failure flag
  - ttf_minutes        → Time to failure in minutes
  - failure_within_horizon → Prediction target (60min horizon)
  - event_*_active     → Event type flags
  - degradation_active → System degradation flag
    """)
    
    print("="*60)
    print("NEXT STEPS")
    print("="*60)
    print("""
1. Load data into InfluxDB:
   influx -username users -password user123123 -database datain \\
     -import -path tick_synthetic_pm_dataset.csv

2. Configure Kapacitor for point-by-point processing
3. Train ML model on labeled data
4. Deploy model predictions back to InfluxDB
    """)


if __name__ == "__main__":
    main()
