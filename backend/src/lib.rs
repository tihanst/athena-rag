use pyo3::prelude::*;

/// A simple function exposed to Python
#[pyfunction]
fn rust_is_working() -> PyResult<String> {
    Ok("Hello from Rust!".to_string())
}

/// Your Python module definition
#[pymodule]
fn rag_portal_backend(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rust_is_working, m)?)?;
    Ok(())
}

