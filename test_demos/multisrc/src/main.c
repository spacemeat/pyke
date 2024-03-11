#include "abc.h"
#include <stdio.h>

int main()
{
#ifdef SINGLE_SRC
	printf("moo");
#else
	printf("total: %i", a() + b() + c() + aa() + bb());
#endif
}

