all:
	cd src; $(MAKE)

install:
	cd src; $(MAKE) install

clean:
	cd src; $(MAKE) clean
	rm -rf build dist *~ MANIFEST tests/curlmodule.so
	rm -rf tests/*~ tests/*.pyc tests/*.pyo tests/header tests/body
