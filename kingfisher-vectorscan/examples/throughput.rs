//! Repeatable synthetic block-scan measurements; no credentials or network access.
//! Run the same executable source/compiler/corpus against each native archive.
use kingfisher_vectorscan::{BlockDatabase, BlockScanner, Flag, Pattern, Scan};
use std::{
    hint::black_box,
    time::{Duration, Instant},
};

fn patterns() -> Vec<Pattern> {
    (0..128)
        .map(|id| {
            Pattern::new(
                format!(r"\btoken_{id:03}_[A-Za-z0-9]{{24}}\b").into_bytes(),
                Flag::default(),
                Some(id),
            )
        })
        .collect()
}

fn input(kind: &str) -> Vec<u8> {
    let mut data = Vec::with_capacity(8 * 1024 * 1024);
    let mut row = 0;
    while data.len() < 8 * 1024 * 1024 {
        if kind == "dense" || (kind == "sparse" && row % 1024 == 0) {
            data.extend_from_slice(
                format!("token_{:03}_a9B2c7D4e1F8g3H6i5J0k2L7\n", row % 128).as_bytes(),
            );
        } else {
            data.extend_from_slice(
                b"ordinary synthetic application configuration; no matching token here\n",
            );
        }
        row += 1;
    }
    data
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let milliseconds: u64 = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "1000".into())
        .parse()?;
    if milliseconds == 0 {
        return Err("measurement duration must be positive".into());
    }
    let compile_start = Instant::now();
    let mut databases = Vec::new();
    for _ in 0..5 {
        databases.push(BlockDatabase::new(patterns())?);
    }
    let compile_ms = compile_start.elapsed().as_secs_f64() * 1000.0 / 5.0;
    let database = databases.pop().unwrap();
    drop(databases);
    let mut scanner = BlockScanner::new(&database)?;
    println!("engine\t{}", kingfisher_vectorscan::version());
    println!("compile_ms\t{compile_ms:.3}");
    println!("database_bytes\t{}", database.size()?);
    println!("scenario\tmib_per_second\tmatches_per_scan\tscans");
    for kind in ["none", "sparse", "dense"] {
        let data = input(kind);
        let mut expected = 0u64;
        scanner.scan(&data, |_, _, _, _| {
            expected += 1;
            Scan::Continue
        })?;
        if (kind == "none") != (expected == 0) {
            return Err("unexpected synthetic match count".into());
        }
        for _ in 0..16 {
            scanner.scan(&data, |_, _, _, _| Scan::Continue)?;
        }
        let start = Instant::now();
        let mut scans = 0u64;
        let mut matches = 0u64;
        loop {
            scanner.scan(black_box(&data), |_, _, _, _| {
                matches += 1;
                Scan::Continue
            })?;
            scans += 1;
            if scans % 16 == 0 && start.elapsed() >= Duration::from_millis(milliseconds) {
                break;
            }
        }
        let seconds = start.elapsed().as_secs_f64();
        if black_box(matches) != expected * scans {
            return Err("scan results changed during measurement".into());
        }
        let throughput = data.len() as f64 * scans as f64 / (1024.0 * 1024.0) / seconds;
        println!("{kind}\t{throughput:.3}\t{expected}\t{scans}");
    }
    Ok(())
}
