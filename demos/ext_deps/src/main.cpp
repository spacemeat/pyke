#include "humon/humon.hpp"
//#include <iostream>
#include "fmt/base.h"

int main()
{
	auto src = "{foo:bar}";

	auto h = hu::Trove::fromString(src);
	if (auto t = std::get_if<hu::Trove>(& h))
	{
		auto foobar = *t / "foo" % hu::val<std::string_view> {};
		fmt::print("{}", foobar);
	}
	else
	{
		fmt::print("plugh");
	}
}

