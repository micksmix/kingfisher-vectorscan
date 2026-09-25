use kingfisher_vectorscan::{BlockDatabase, BlockScanner, Flag, Pattern, Scan};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let database =
        BlockDatabase::new(vec![Pattern::new(b"hello".to_vec(), Flag::default(), None)])?;
    let mut scanner = BlockScanner::new(&database)?;
    scanner.scan(b"hello world", |id, _from, to, _flags| {
        println!("Pattern {id} matched, ending at byte {to}");
        Scan::Continue
    })?;
    Ok(())
}
