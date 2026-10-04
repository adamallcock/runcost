package ledger

import (
	"fmt"
	"math/big"
	"strings"
)

func rat(value any) *big.Rat {
	parsed, ok := new(big.Rat).SetString(numberString(value))
	if !ok {
		panic(fmt.Sprintf("invalid decimal: %v", value))
	}
	return parsed
}

func decimal(value *big.Rat) string {
	if value.Sign() == 0 {
		return "0"
	}
	const places = 18
	scale := new(big.Int).Exp(big.NewInt(10), big.NewInt(places), nil)
	numerator := new(big.Int).Abs(new(big.Int).Set(value.Num()))
	numerator.Mul(numerator, scale)
	denominator := new(big.Int).Set(value.Denom())
	quotient := new(big.Int)
	remainder := new(big.Int)
	quotient.QuoRem(numerator, denominator, remainder)
	twiceRemainder := new(big.Int).Lsh(new(big.Int).Set(remainder), 1)
	comparison := twiceRemainder.Cmp(denominator)
	if comparison > 0 || (comparison == 0 && quotient.Bit(0) == 1) {
		quotient.Add(quotient, big.NewInt(1))
	}
	if quotient.Sign() == 0 {
		return "0"
	}
	digits := quotient.String()
	if len(digits) <= places {
		digits = strings.Repeat("0", places-len(digits)+1) + digits
	}
	whole := digits[:len(digits)-places]
	fraction := strings.TrimRight(digits[len(digits)-places:], "0")
	text := whole
	if fraction != "" {
		text += "." + fraction
	}
	if value.Sign() < 0 {
		text = "-" + text
	}
	return text
}

func add(left any, right any) string {
	return decimal(new(big.Rat).Add(rat(left), rat(right)))
}

func subtract(left any, right any) string {
	return decimal(new(big.Rat).Sub(rat(left), rat(right)))
}

func multiplyDivide(quantity any, amount any, per any) string {
	perRat := rat(per)
	if perRat.Sign() <= 0 {
		panic("price.per must be greater than zero")
	}
	result := new(big.Rat).Mul(rat(quantity), rat(amount))
	result.Quo(result, perRat)
	return decimal(result)
}
