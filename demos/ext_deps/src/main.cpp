#include <humon/humon.hpp>
#include <iostream>

int main()
{
	auto src = "{foo:bar}";

	auto h = hu::Trove::fromString(src);
	if (auto t = std::get_if<hu::Trove>(& h))
	{
		std::cout << *t / "foo" % hu::val<std::string_view> {};
	}
	else
	{
		std::cout << "plugh";
	}
}

